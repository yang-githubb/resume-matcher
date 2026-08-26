import { afterEach, describe, expect, it, vi } from "vitest";

import { discoverAndMatch } from "@/lib/api";

const PAYLOAD = {
  resume_id: "r1",
  preferences: {
    keywords: "python backend engineer",
    remote_only: true,
    country: "us",
    limit: 25,
  },
};

/** Serves `chunks` as a streamed body, one read per chunk. */
function streamingResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(stream, { status: 200 });
}

const frame = (event: unknown) => `data: ${JSON.stringify(event)}\n\n`;

const RESULT = { session_id: "s1", results: [], fetched_count: 3, ranked_count: 2 };

function mockFetch(response: Response | Promise<Response>) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("discoverAndMatch", () => {
  it("reports each progress event and returns the final result", async () => {
    mockFetch(
      streamingResponse([
        frame({ progress: 0.12, label: "Searching job boards" }),
        frame({ progress: 0.68, label: "Scoring" }),
        frame({ result: RESULT }),
      ]),
    );

    const seen: Array<{ progress: number; label: string }> = [];
    const result = await discoverAndMatch(PAYLOAD, (p) => seen.push(p));

    expect(seen).toEqual([
      { progress: 0.12, label: "Searching job boards" },
      { progress: 0.68, label: "Scoring" },
    ]);
    expect(result).toEqual(RESULT);
  });

  it("reassembles a frame split across chunk boundaries", async () => {
    // The network decides where chunks break, not the server. Splitting mid
    // JSON is the case that silently loses events if the buffer is dropped,
    // so both cuts land strictly inside a frame - a cut that happens to fall
    // on a frame boundary would exercise nothing.
    const first = frame({ progress: 0.5, label: "Scoring" });
    const whole = first + frame({ result: RESULT });
    const insideFirst = 20;
    const insideSecond = first.length + 12;
    expect(insideFirst).toBeLessThan(first.length);
    expect(insideSecond).toBeLessThan(whole.length);

    mockFetch(
      streamingResponse([
        whole.slice(0, insideFirst),
        whole.slice(insideFirst, insideSecond),
        whole.slice(insideSecond),
      ]),
    );

    const seen: Array<{ progress: number; label: string }> = [];
    const result = await discoverAndMatch(PAYLOAD, (p) => seen.push(p));

    expect(seen).toEqual([{ progress: 0.5, label: "Scoring" }]);
    expect(result).toEqual(RESULT);
  });

  it("surfaces an error carried by the stream", async () => {
    mockFetch(
      streamingResponse([
        frame({ progress: 0.12, label: "Searching job boards" }),
        frame({ error: "Adzuna has no JP listings." }),
      ]),
    );

    await expect(discoverAndMatch(PAYLOAD)).rejects.toThrow("Adzuna has no JP listings.");
  });

  it("fails loudly when the stream ends before any result", async () => {
    // A truncated stream must not resolve as an empty success.
    mockFetch(streamingResponse([frame({ progress: 0.4, label: "Scoring" })]));

    await expect(discoverAndMatch(PAYLOAD)).rejects.toThrow(
      "Search ended before returning results.",
    );
  });

  it("reports the server's message when the request itself fails", async () => {
    mockFetch(
      new Response(JSON.stringify({ detail: "resume_id not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(discoverAndMatch(PAYLOAD)).rejects.toThrow("resume_id not found");
  });
});
