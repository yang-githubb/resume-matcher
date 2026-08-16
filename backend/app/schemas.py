from typing import Literal

from pydantic import BaseModel, Field


class StructuredDocument(BaseModel):
    skills: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ParseResponse(BaseModel):
    id: str
    doc_type: Literal["resume", "job"]
    filename: str
    raw_text: str
    structured: StructuredDocument


class JobSummary(BaseModel):
    id: str
    filename: str
    created_at: str


class MatchBreakdown(BaseModel):
    matched_skills: list[str]
    missing_skills: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]


class MatchResultItem(BaseModel):
    id: str
    resume_id: str | None = None
    resume_filename: str | None = None
    job_id: str | None = None
    job_filename: str | None = None
    job_url: str | None = None
    job_company: str | None = None
    job_location: str | None = None
    job_source: str | None = None
    score: float
    semantic_score: float
    keyword_score: float
    breakdown: MatchBreakdown
    explanation: str | None = None


class RankResponse(BaseModel):
    session_id: str
    mode: Literal["seeker", "recruiter"]
    variant: Literal["resumes_for_job", "jobs_for_resume"]
    job_id: str | None = None
    resume_id: str | None = None
    resume_filename: str | None = None
    results: list[MatchResultItem]


class ExplainRequest(BaseModel):
    session_id: str
    result_id: str


class ExplainResponse(BaseModel):
    result_id: str
    explanation: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    result_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    messages: list[dict[str, str]]


class SessionSummary(BaseModel):
    id: str
    mode: str
    job_id: str | None = None
    resume_id: str | None = None
    job_filename: str | None = None
    resume_filename: str | None = None
    created_at: str


class HealthResponse(BaseModel):
    status: str
    ollama_model: str
    embedding_model: str
    weights: dict[str, float]


class TextDocumentRequest(BaseModel):
    doc_type: Literal["resume", "job"]
    text: str = Field(min_length=30)
    label: str = "pasted.txt"


class UpdateDocumentRequest(BaseModel):
    raw_text: str = Field(min_length=20)
