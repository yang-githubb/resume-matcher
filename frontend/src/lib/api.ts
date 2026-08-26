import type {
  ChatResponse,
  DiscoverResponse,
  HealthResponse,
  JobSummary,
  ParseResponse,
  RankResponse,
  SearchPreferences,
  SessionSummary,
  SourceInfo,
} from "@/types/api";

const API_BASE = "/api";

async function parseError(response: Response, fallback: string): Promise<string> {
  const body = await response.text();
  try {
    const json = JSON.parse(body) as { detail?: string | Array<{ msg: string }> };
    if (typeof json.detail === "string") return json.detail;
    if (Array.isArray(json.detail)) return json.detail.map((d) => d.msg).join(", ");
  } catch {
    // not JSON
  }
  return body || fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(await parseError(response, `Request failed (${response.status})`));
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function uploadDocument(
  docType: "resume" | "job",
  file: File,
): Promise<ParseResponse> {
  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);
  return request<ParseResponse>("/documents/upload", { method: "POST", body: form });
}

export async function createTextDocument(payload: {
  doc_type: "resume" | "job";
  text: string;
  label?: string;
}): Promise<ParseResponse> {
  return request<ParseResponse>("/documents/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listJobs(
  origin: "manual" | "discovered" | "all" = "manual",
): Promise<JobSummary[]> {
  return request<JobSummary[]>(`/documents/jobs?origin=${origin}`);
}

export async function deleteJob(jobId: string): Promise<void> {
  await request(`/documents/${jobId}`, { method: "DELETE" });
}

export async function getSources(): Promise<SourceInfo[]> {
  return request<SourceInfo[]>("/discover/sources");
}

export interface SearchProgress {
  progress: number;
  label: string;
}

interface DiscoverPayload {
  resume_id: string;
  preferences: SearchPreferences;
  explain?: boolean;
  explain_top?: number;
  min_score?: number;
}

/**
 * Runs a search, reporting progress as the server works through it.
 *
 * The server streams newline-delimited SSE frames; the final one carries the
 * results. A plain POST would leave the user staring at a spinner for the
 * length of a fetch, a scoring pass and several LLM calls.
 */
export async function discoverAndMatch(
  payload: DiscoverPayload,
  onProgress?: (progress: SearchProgress) => void,
): Promise<DiscoverResponse> {
  const response = await fetch(`${API_BASE}/discover/match/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    throw new Error(await parseError(response, `Search failed (${response.status})`));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: DiscoverResponse | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;

      const event = JSON.parse(line.slice(5).trim());
      if (event.error) throw new Error(event.error);
      if (event.result) {
        result = event.result as DiscoverResponse;
      } else {
        onProgress?.({ progress: event.progress, label: event.label });
      }
    }
  }

  if (!result) throw new Error("Search ended before returning results.");
  return result;
}

export async function getSession(sessionId: string): Promise<RankResponse> {
  return request<RankResponse>(`/sessions/${sessionId}`);
}

export async function sendChat(payload: {
  session_id: string;
  message: string;
  result_id?: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/sessions");
}

export async function getChatHistory(
  sessionId: string,
): Promise<{ messages: Array<{ role: string; content: string }> }> {
  return request(`/chat/${sessionId}`);
}

export function exportSessionUrl(sessionId: string): string {
  return `${API_BASE}/sessions/${sessionId}/export`;
}
