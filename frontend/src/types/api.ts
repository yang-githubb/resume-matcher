export interface StructuredDocument {
  skills: string[];
  titles: string[];
  keywords: string[];
}

export interface ParseResponse {
  id: string;
  doc_type: "resume" | "job";
  filename: string;
  raw_text: string;
  structured: StructuredDocument;
}

export interface JobSummary {
  id: string;
  filename: string;
  created_at: string;
  origin: "manual" | "discovered";
  source?: string | null;
  url?: string | null;
  company?: string | null;
  location?: string | null;
}

export interface MatchBreakdown {
  matched_skills: string[];
  missing_skills: string[];
  matched_keywords: string[];
  missing_keywords: string[];
}

export interface MatchResultItem {
  id: string;
  resume_id?: string | null;
  job_id?: string | null;
  job_filename?: string | null;
  job_url?: string | null;
  job_company?: string | null;
  job_location?: string | null;
  job_source?: string | null;
  score: number;
  semantic_score: number;
  keyword_score: number;
  breakdown: MatchBreakdown;
  explanation: string | null;
}

export interface RankResponse {
  session_id: string;
  resume_id?: string | null;
  resume_filename?: string | null;
  results: MatchResultItem[];
}

export interface ChatResponse {
  reply: string;
  messages: Array<{ role: string; content: string }>;
}

export interface SessionSummary {
  id: string;
  resume_id?: string | null;
  resume_filename?: string | null;
  created_at: string;
}

export interface SourceInfo {
  name: string;
  label: string;
  requires_key: boolean;
  available: boolean;
}

export interface SourceReport {
  name: string;
  label: string;
  fetched: number;
  error: string | null;
}

export interface SearchPreferences {
  keywords: string;
  location?: string | null;
  seniority?: string | null;
  remote_only: boolean;
  country: string;
  limit: number;
  sources?: string[] | null;
}

export interface DiscoverResponse extends RankResponse {
  sources: SourceReport[];
  fetched_count: number;
  ranked_count: number;
}

export interface HealthResponse {
  status: string;
  ollama_model: string;
  embedding_model: string;
  weights: { semantic: number; keyword: number };
}
