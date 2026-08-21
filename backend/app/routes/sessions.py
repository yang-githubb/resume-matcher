from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app import db
from app.schemas import MatchBreakdown, MatchResultItem, RankResponse, SessionSummary
from app.services.export import build_session_markdown

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _result_item(row: dict) -> MatchResultItem:
    return MatchResultItem(
        id=row["id"],
        job_id=row["job_id"],
        job_filename=row["job_filename"],
        job_url=row.get("job_url"),
        job_company=row.get("job_company"),
        job_location=row.get("job_location"),
        job_source=row.get("job_source"),
        resume_id=row.get("resume_id"),
        score=row["score"],
        semantic_score=row["semantic_score"],
        keyword_score=row["keyword_score"],
        breakdown=MatchBreakdown(**row["breakdown"]),
        explanation=row["explanation"],
    )


@router.get("", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    return [SessionSummary(**item) for item in db.list_sessions()]


@router.get("/{session_id}", response_model=RankResponse)
async def get_session(session_id: str) -> RankResponse:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    resume = db.get_document(session["resume_id"]) if session.get("resume_id") else None
    return RankResponse(
        session_id=session_id,
        resume_id=session.get("resume_id"),
        resume_filename=resume["filename"] if resume else None,
        results=[_result_item(row) for row in db.get_session_results(session_id)],
    )


@router.get("/{session_id}/export")
async def export_session(session_id: str) -> PlainTextResponse:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    markdown = build_session_markdown(session, db.get_session_results(session_id))
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="match-{session_id[:8]}.md"'},
    )
