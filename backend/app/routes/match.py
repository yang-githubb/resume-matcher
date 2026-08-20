from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app import db
from app.explain.ollama import generate_explanation
from app.schemas import ExplainRequest, ExplainResponse, MatchBreakdown, MatchResultItem, RankResponse
from app.services.export import build_session_markdown

router = APIRouter(prefix="/match", tags=["match"])


def _result_item_from_row(item: dict) -> MatchResultItem:
    return MatchResultItem(
        id=item["id"],
        job_id=item["job_id"],
        job_filename=item["job_filename"],
        job_url=item.get("job_url"),
        job_company=item.get("job_company"),
        job_location=item.get("job_location"),
        job_source=item.get("job_source"),
        resume_id=item.get("resume_id"),
        score=item["score"],
        semantic_score=item["semantic_score"],
        keyword_score=item["keyword_score"],
        breakdown=MatchBreakdown(**item["breakdown"]),
        explanation=item["explanation"],
    )


@router.get("/sessions/{session_id}", response_model=RankResponse)
async def get_session(session_id: str) -> RankResponse:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    resume = db.get_document(session["resume_id"]) if session.get("resume_id") else None
    return RankResponse(
        session_id=session_id,
        resume_id=session.get("resume_id"),
        resume_filename=resume["filename"] if resume else None,
        results=[_result_item_from_row(item) for item in db.get_session_results(session_id)],
    )


@router.post("/explain", response_model=ExplainResponse)
async def explain_match(request: ExplainRequest) -> ExplainResponse:
    session = db.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    results = db.get_session_results(request.session_id)
    target = next((r for r in results if r["id"] == request.result_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Match result not found.")

    resume = db.get_document(session["resume_id"])
    job = db.get_document(target["job_id"])
    if job is None or resume is None:
        raise HTTPException(status_code=404, detail="Linked documents not found.")

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
