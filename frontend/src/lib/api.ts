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

export async function updateDocumentText(
  docId: string,
  rawText: string,
): Promise<ParseResponse> {
  return request<ParseResponse>(`/documents/${docId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText }),
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

export async function rankJobsForResume(payload: {
  resume_id: string;
  job_ids?: string[];
  explain?: boolean;
  explain_top?: number;
}): Promise<RankResponse> {
  return request<RankResponse>("/match/rank-jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function rankDocuments(payload: {
  mode: "seeker" | "recruiter";
  job_id: string;
  resume_ids: string[];
  explain?: boolean;
}): Promise<RankResponse> {
  return request<RankResponse>("/match/rank", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listSources(): Promise<SourceInfo[]> {
  return request<SourceInfo[]>("/discover/sources");
}

export async function discoverAndMatch(payload: {
  resume_id: string;
  preferences: SearchPreferences;
  explain?: boolean;
  explain_top?: number;
  min_score?: number;
}): Promise<DiscoverResponse> {
  return request<DiscoverResponse>("/discover/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getSession(sessionId: string): Promise<RankResponse> {
  return request<RankResponse>(`/match/sessions/${sessionId}`);
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
  return `${API_BASE}/match/sessions/${sessionId}/export`;
}
