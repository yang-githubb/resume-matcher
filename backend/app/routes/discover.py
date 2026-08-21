from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import db
from app.explain.ollama import generate_explanation
from app.matching.scorer import hybrid_score
from app.parsers.document import structure_text
from app.schemas import MatchBreakdown, MatchResultItem, RankResponse
from app.sources import registry
from app.sources.base import FetchedJob, JobQuery

router = APIRouter(prefix="/discover", tags=["discover"])

MAX_FETCH = 50
MAX_LIBRARY_JOBS = 25
EXPLAIN_TOP_DEFAULT = 3

# Fractions of the progress bar each phase owns, in order. Scoring and analysis
# get the biggest shares because they are what actually takes the time.
PROGRESS_SEARCH = 0.12
PROGRESS_COLLECT = 0.22
PROGRESS_SCORE = 0.68
PROGRESS_ANALYSE = 1.0


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
    # Hand-added postings are scored alongside the search results so a single
    # action ranks everything the user cares about.
    include_library: bool = True
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


def _step(start: float, end: float, done: int, total: int) -> float:
    """Position within a phase's slice of the bar."""
    if total <= 0:
        return end
    return start + (end - start) * (done / total)


async def _run_discovery(request: DiscoverMatchRequest) -> AsyncIterator[dict[str, Any]]:
    """Run a search, yielding progress as it goes; the last event carries the result.

    The work is split into phases whose real cost the caller cannot predict -
    fetching, scoring and writing analyses each dominate under different
    settings - so progress is reported from here rather than guessed at.
    """
    resume = db.get_document(request.resume_id)
    if resume is None or resume["doc_type"] != "resume":
        raise HTTPException(status_code=404, detail="Resume not found.")

    yield {"progress": 0.02, "label": "Searching job boards..."}

    preferences = request.preferences
    outcome = await registry.search(preferences.to_query(), preferences.sources)

    yield {"progress": PROGRESS_SEARCH, "label": f"Found {len(outcome.jobs)} postings"}

    # Persist first so the ranker and every later session read the same rows.
    jobs: list[dict] = []
    meta: dict[str, FetchedJob] = {}
    seen: set[str] = set()
    total_fetched = len(outcome.jobs)
    for index, fetched in enumerate(outcome.jobs, start=1):
        doc_id = _persist_job(fetched)
        if doc_id not in seen:
            document = db.get_document(doc_id)
            if document is not None:
                seen.add(doc_id)
                jobs.append(document)
                meta[doc_id] = fetched
        yield {
            "progress": _step(PROGRESS_SEARCH, PROGRESS_COLLECT, index, total_fetched),
            "label": f"Reading postings ({index}/{total_fetched})",
        }

    # Postings already in the library are scored too. Only hand-added ones:
    # re-ranking every previously discovered job would grow without bound and
    # bury fresh results under stale ones.
    if request.include_library:
        for summary in db.list_jobs(MAX_LIBRARY_JOBS, origin="manual"):
            if summary["id"] in seen:
                continue
            document = db.get_document(summary["id"])
            if document is not None:
                seen.add(summary["id"])
                jobs.append(document)

    if not jobs:
        errors = [f"{s.label}: {s.error}" for s in outcome.sources if s.error]
        detail = "No jobs found for those preferences."
        if errors:
            detail += " Sources reported: " + "; ".join(errors)
        raise HTTPException(status_code=502 if errors else 404, detail=detail)

    scored: list[dict[str, Any]] = []
    for index, job in enumerate(jobs, start=1):
        scored.append({"job": job, **hybrid_score(resume, job)})
        yield {
            "progress": _step(PROGRESS_COLLECT, PROGRESS_SCORE, index, len(jobs)),
            "label": f"Scoring against your resume ({index}/{len(jobs)})",
        }
        # Scoring is blocking CPU work; let the response flush between jobs.
        await asyncio.sleep(0)

    ranked = sorted(scored, key=lambda item: item["score"], reverse=True)
    if request.min_score > 0:
        ranked = [item for item in ranked if item["score"] >= request.min_score]

    if not ranked:
        raise HTTPException(
            status_code=404,
            detail=f"Found {len(jobs)} jobs but none scored above "
            f"{request.min_score:.0f}%. Lower the minimum score or widen your keywords.",
        )

    session_id = db.create_match_session(resume_id=resume["id"])
    explain_total = min(request.explain_top, len(ranked)) if request.explain else 0

    results: list[MatchResultItem] = []
    for index, item in enumerate(ranked):
        job = item["job"]
        breakdown = item["breakdown"]
        should_explain = index < explain_total

        if should_explain:
            yield {
                "progress": _step(PROGRESS_SCORE, PROGRESS_ANALYSE, index, explain_total),
                "label": f"Writing analysis ({index + 1}/{explain_total})",
            }

        explanation = (
            await generate_explanation(
                resume,
                job,
                breakdown,
                {
                    "score": item["score"],
                    "semantic_score": item["semantic_score"],
                    "keyword_score": item["keyword_score"],
                },
            )
            if should_explain
            else None
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

    yield {
        "progress": 1.0,
        "label": "Done",
        "result": DiscoverResponse(
            session_id=session_id,
            resume_id=resume["id"],
            resume_filename=resume["filename"],
            results=results,
            sources=[SourceReport(**vars(s)) for s in outcome.sources],
            fetched_count=len(outcome.jobs),
            ranked_count=len(results),
        ),
    }


@router.post("/match", response_model=DiscoverResponse)
async def discover_and_match(request: DiscoverMatchRequest) -> DiscoverResponse:
    async for event in _run_discovery(request):
        if "result" in event:
            return event["result"]
    raise HTTPException(status_code=500, detail="Search finished without a result.")


@router.post("/match/stream")
async def discover_and_match_stream(request: DiscoverMatchRequest) -> StreamingResponse:
    """Same work as /match, but reports progress while it runs."""

    async def events() -> AsyncIterator[str]:
        try:
            async for event in _run_discovery(request):
                payload = dict(event)
                result = payload.pop("result", None)
                if result is not None:
                    payload["result"] = result.model_dump(mode="json")
                yield f"data: {json.dumps(payload)}\n\n"
        except HTTPException as exc:
            yield f"data: {json.dumps({'error': exc.detail})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
