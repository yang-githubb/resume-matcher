from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app import db
from app.explain.ollama import generate_explanation
from app.matching.scorer import rank_jobs, rank_resumes
from app.schemas import ExplainRequest, ExplainResponse, MatchBreakdown, MatchResultItem, RankResponse
from app.services.export import build_session_markdown

router = APIRouter(prefix="/match", tags=["match"])

MAX_RESUMES = 2
MAX_JOBS = 50
EXPLAIN_TOP_DEFAULT = 5


class RankRequest(BaseModel):
    mode: Literal["seeker", "recruiter"]
    job_id: str
    resume_ids: list[str] = Field(min_length=1, max_length=MAX_RESUMES)
    explain: bool = True


class RankJobsRequest(BaseModel):
    resume_id: str
    job_ids: list[str] | None = None
    explain: bool = True
    explain_top: int = Field(default=EXPLAIN_TOP_DEFAULT, ge=0, le=MAX_JOBS)


def _result_item_from_recruiter_row(item: dict) -> MatchResultItem:
    return MatchResultItem(
        id=item["id"],
        resume_id=item["resume_id"],
        resume_filename=item["resume_filename"],
        job_id=item.get("job_id"),
        score=item["score"],
        semantic_score=item["semantic_score"],
        keyword_score=item["keyword_score"],
        breakdown=MatchBreakdown(**item["breakdown"]),
        explanation=item["explanation"],
    )


def _result_item_from_seeker_row(item: dict) -> MatchResultItem:
    return MatchResultItem(
        id=item["id"],
        job_id=item["job_id"],
        job_filename=item["job_filename"],
        resume_id=item.get("resume_id"),
        score=item["score"],
        semantic_score=item["semantic_score"],
        keyword_score=item["keyword_score"],
        breakdown=MatchBreakdown(**item["breakdown"]),
        explanation=item["explanation"],
    )


def _session_variant(session: dict) -> Literal["resumes_for_job", "jobs_for_resume"]:
    if session.get("resume_id") and not session.get("job_id"):
        return "jobs_for_resume"
    return "resumes_for_job"


async def _maybe_explain(
    resume: dict,
    job: dict,
    breakdown: dict,
    scores: dict[str, float],
    explain: bool,
) -> str | None:
    if not explain:
        return None
    return await generate_explanation(resume, job, breakdown, scores)


@router.post("/rank", response_model=RankResponse)
async def rank(request: RankRequest) -> RankResponse:
    job = db.get_document(request.job_id)
    if job is None or job["doc_type"] != "job":
        raise HTTPException(status_code=404, detail="Job document not found.")

    resumes = []
    for resume_id in request.resume_ids:
        resume = db.get_document(resume_id)
        if resume is None or resume["doc_type"] != "resume":
            raise HTTPException(status_code=404, detail=f"Resume not found: {resume_id}")
        resumes.append(resume)

    ranked = rank_resumes(resumes, job)
    session_id = db.create_match_session(request.mode, job_id=request.job_id)

    results: list[MatchResultItem] = []
    for item in ranked:
        resume = item["resume"]
        breakdown = item["breakdown"]
        scores = {
            "score": item["score"],
            "semantic_score": item["semantic_score"],
            "keyword_score": item["keyword_score"],
        }
        explanation = await _maybe_explain(resume, job, breakdown, scores, request.explain)

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

        results.append(
            MatchResultItem(
                id=result_id,
                resume_id=resume["id"],
                resume_filename=resume["filename"],
                job_id=job["id"],
                score=item["score"],
                semantic_score=item["semantic_score"],
                keyword_score=item["keyword_score"],
                breakdown=MatchBreakdown(**breakdown),
                explanation=explanation,
            )
        )

    return RankResponse(
        session_id=session_id,
        mode=request.mode,
        variant="resumes_for_job",
        job_id=request.job_id,
        results=results,
    )


@router.post("/rank-jobs", response_model=RankResponse)
async def rank_jobs_for_resume(request: RankJobsRequest) -> RankResponse:
    resume = db.get_document(request.resume_id)
    if resume is None or resume["doc_type"] != "resume":
        raise HTTPException(status_code=404, detail="Resume not found.")

    if request.job_ids:
        job_ids = request.job_ids[:MAX_JOBS]
    else:
        job_ids = [job["id"] for job in db.list_jobs(MAX_JOBS)]

    if not job_ids:
        raise HTTPException(
            status_code=400,
            detail="No jobs in your library. Add job postings first.",
        )

    jobs = []
    for job_id in job_ids:
        job = db.get_document(job_id)
        if job is None or job["doc_type"] != "job":
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        jobs.append(job)

    ranked = rank_jobs(jobs, resume)
    session_id = db.create_match_session("seeker", resume_id=resume["id"])

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
        explanation = await _maybe_explain(resume, job, breakdown, scores, should_explain)

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

        results.append(
            MatchResultItem(
                id=result_id,
                job_id=job["id"],
                job_filename=job["filename"],
                resume_id=resume["id"],
                score=item["score"],
                semantic_score=item["semantic_score"],
                keyword_score=item["keyword_score"],
                breakdown=MatchBreakdown(**breakdown),
                explanation=explanation,
            )
        )

    return RankResponse(
        session_id=session_id,
        mode="seeker",
        variant="jobs_for_resume",
        resume_id=resume["id"],
        resume_filename=resume["filename"],
        results=results,
    )


@router.get("/sessions/{session_id}", response_model=RankResponse)
async def get_session(session_id: str) -> RankResponse:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    raw_results = db.get_session_results(session_id)
    variant = _session_variant(session)

    if variant == "jobs_for_resume":
        resume = db.get_document(session["resume_id"]) if session.get("resume_id") else None
        results = [_result_item_from_seeker_row(item) for item in raw_results]
        return RankResponse(
            session_id=session_id,
            mode=session["mode"],
            variant=variant,
            resume_id=session.get("resume_id"),
            resume_filename=resume["filename"] if resume else None,
            results=results,
        )

    results = [_result_item_from_recruiter_row(item) for item in raw_results]
    return RankResponse(
        session_id=session_id,
        mode=session["mode"],
        variant=variant,
        job_id=session.get("job_id"),
        results=results,
    )


def _resolve_match_documents(session: dict, target: dict) -> tuple[dict, dict]:
    if _session_variant(session) == "jobs_for_resume":
        resume = db.get_document(session["resume_id"])
        job = db.get_document(target["job_id"])
    else:
        job = db.get_document(session["job_id"])
        resume = db.get_document(target["resume_id"])
    if job is None or resume is None:
        raise HTTPException(status_code=404, detail="Linked documents not found.")
    return resume, job


@router.post("/explain", response_model=ExplainResponse)
async def explain_match(request: ExplainRequest) -> ExplainResponse:
    session = db.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    results = db.get_session_results(request.session_id)
    target = next((r for r in results if r["id"] == request.result_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Match result not found.")

    resume, job = _resolve_match_documents(session, target)
    explanation = await generate_explanation(
        resume,
        job,
        target["breakdown"],
        {
            "score": target["score"],
            "semantic_score": target["semantic_score"],
            "keyword_score": target["keyword_score"],
        },
    )
    db.update_match_explanation(request.result_id, explanation)

    return ExplainResponse(result_id=request.result_id, explanation=explanation)


@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str) -> PlainTextResponse:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    results = db.get_session_results(session_id)
    markdown = build_session_markdown(session, results)
    filename = f"match-{session_id[:8]}.md"
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
