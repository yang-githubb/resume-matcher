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
  resume_filename?: string | null;
  job_id?: string | null;
  job_filename?: string | null;
  score: number;
  semantic_score: number;
  keyword_score: number;
  breakdown: MatchBreakdown;
  explanation: string | null;
}

export interface RankResponse {
  session_id: string;
  mode: "seeker" | "recruiter";
  variant: "resumes_for_job" | "jobs_for_resume";
  job_id?: string | null;
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
  mode: string;
  job_id?: string | null;
  resume_id?: string | null;
  job_filename?: string | null;
  resume_filename?: string | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  ollama_model: string;
  embedding_model: string;
  weights: { semantic: number; keyword: number };
}
