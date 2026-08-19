from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.explain.ollama import generate_explanation
from app.matching.scorer import rank_jobs
from app.parsers.document import structure_text
from app.schemas import MatchBreakdown, MatchResultItem, RankResponse
from app.sources import registry
from app.sources.base import FetchedJob, JobQuery

router = APIRouter(prefix="/discover", tags=["discover"])

MAX_FETCH = 50
EXPLAIN_TOP_DEFAULT = 3


class SearchPreferences(BaseModel):
    """The basic info collected before any board is contacted."""

    keywords: str = Field(min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    seniority: str | None = Field(default=None, max_length=40)
    remote_only: bool = False
    country: str = Field(default="gb", max_length=2)
    limit: int = Field(default=25, ge=1, le=MAX_FETCH)
    sources: list[str] | None = None
    min_relevance: float = Field(default=0.3, ge=0.0, le=1.0)

    def to_query(self) -> JobQuery:
        keywords = self.keywords.strip()
        # Seniority is folded into the search text: every board understands
        # free-text terms, but few expose a structured level filter.
        if self.seniority and self.seniority.strip():
            keywords = f"{self.seniority.strip()} {keywords}"
        return JobQuery(
            keywords=keywords,
            location=self.location,
            remote_only=self.remote_only,
            country=self.country,
            limit=self.limit,
            min_relevance=self.min_relevance,
        )


class DiscoverMatchRequest(BaseModel):
    resume_id: str
    preferences: SearchPreferences
    explain: bool = True
    explain_top: int = Field(default=EXPLAIN_TOP_DEFAULT, ge=0, le=10)
    # Scores are on a 0-100 scale throughout the app, matching hybrid_score.
    min_score: float = Field(default=0.0, ge=0.0, le=100.0)


class SourceReport(BaseModel):
    name: str
    label: str
    fetched: int
    error: str | None = None


class SourceInfo(BaseModel):
    name: str
    label: str
    requires_key: bool
    available: bool


class DiscoverResponse(RankResponse):
    sources: list[SourceReport]
    fetched_count: int
    ranked_count: int


@router.get("/sources", response_model=list[SourceInfo])
async def list_sources() -> list[SourceInfo]:
    return [SourceInfo(**info) for info in registry.available_sources()]


def _persist_job(job: FetchedJob) -> str:
    """Store a fetched posting as a job document, reusing it if already seen."""
    existing = db.find_job_by_external(job.source, job.external_id)
    if existing:
        return existing

    text = job.to_document_text()
    return db.insert_document(
        "job",
        job.label,
        text,
        structure_text(text),
        origin="discovered",
        source=job.source,
        external_id=job.external_id,
        url=job.url,
        company=job.company,
        location=job.location,
    )


@router.post("/match", response_model=DiscoverResponse)
async def discover_and_match(request: DiscoverMatchRequest) -> DiscoverResponse:
    resume = db.get_document(request.resume_id)
    if resume is None or resume["doc_type"] != "resume":
        raise HTTPException(status_code=404, detail="Resume not found.")

    preferences = request.preferences
    outcome = await registry.search(preferences.to_query(), preferences.sources)

    if not outcome.jobs:
        errors = [f"{s.label}: {s.error}" for s in outcome.sources if s.error]
        detail = "No jobs found for those preferences."
        if errors:
            detail += " Sources reported: " + "; ".join(errors)
        raise HTTPException(status_code=502 if errors else 404, detail=detail)

    # Persist first so the ranker and every later session read the same rows.
    jobs: list[dict] = []
    meta: dict[str, FetchedJob] = {}
    for fetched in outcome.jobs:
        doc_id = _persist_job(fetched)
        document = db.get_document(doc_id)
        if document is None:
            continue
        jobs.append(document)
        meta[doc_id] = fetched

    ranked = rank_jobs(jobs, resume)
    if request.min_score > 0:
        ranked = [item for item in ranked if item["score"] >= request.min_score]

    if not ranked:
        raise HTTPException(
            status_code=404,
            detail=f"Found {len(outcome.jobs)} jobs but none scored above "
            f"{request.min_score:.0f}%. Lower the minimum score or widen your keywords.",
        )

    session_id = db.create_match_session(resume_id=resume["id"])

    results: list[MatchResultItem] = []
    for index, item in enumerate(ranked):
        job = item["job"]
        breakdown = item["breakdown"]
        scores = {
            "score": item["score"],
            "semantic_score": item["semantic_score"],
            "keyword_score": item["keyword_score"],
        }
        should_explain = request.explain and index < request.explain_top
        explanation = (
            await generate_explanation(resume, job, breakdown, scores) if should_explain else None
        )

        result_id = db.insert_match_result(
            session_id,
            item["score"],
            item["semantic_score"],
            item["keyword_score"],
            breakdown,
            resume_id=resume["id"],
            job_id=job["id"],
            explanation=explanation,
        )

        source_job = meta.get(job["id"])
        results.append(
            MatchResultItem(
                id=result_id,
                job_id=job["id"],
                job_filename=job["filename"],
                job_url=source_job.url if source_job else None,
                job_company=source_job.company if source_job else None,
                job_location=source_job.location if source_job else None,
                job_source=source_job.source if source_job else None,
                resume_id=resume["id"],
                score=item["score"],
                semantic_score=item["semantic_score"],
                keyword_score=item["keyword_score"],
                breakdown=MatchBreakdown(**breakdown),
                explanation=explanation,
            )
        )

    return DiscoverResponse(
        session_id=session_id,
        resume_id=resume["id"],
        resume_filename=resume["filename"],
        results=results,
        sources=[SourceReport(**vars(s)) for s in outcome.sources],
        fetched_count=len(outcome.jobs),
        ranked_count=len(results),
    )
