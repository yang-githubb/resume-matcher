from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import db
from app.explain.ollama import chat_about_match
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _resolve_from_session(session: dict, target: dict) -> tuple[dict, dict]:
    resume = db.get_document(session["resume_id"])
    job = db.get_document(target["job_id"])
    if job is None or resume is None:
        raise HTTPException(status_code=404, detail="Linked documents not found.")
    return resume, job


@router.get("/{session_id}")
async def get_chat_history(session_id: str) -> dict[str, list[dict[str, str]]]:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"messages": db.get_chat_messages(session_id)}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session = db.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    results = db.get_session_results(request.session_id)
    if not results:
        raise HTTPException(status_code=400, detail="No match results in this session.")

    if request.result_id:
        target = next((r for r in results if r["id"] == request.result_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="Match result not found.")
    else:
        target = results[0]

    resume, job = _resolve_from_session(session, target)

    history = db.get_chat_messages(request.session_id)
    db.insert_chat_message(request.session_id, "user", request.message)

    reply = await chat_about_match(
        resume,
        job,
        target["breakdown"],
        {
            "score": target["score"],
            "semantic_score": target["semantic_score"],
            "keyword_score": target["keyword_score"],
        },
        history,
        request.message,
    )
    db.insert_chat_message(request.session_id, "assistant", reply)

    messages = db.get_chat_messages(request.session_id)
    return ChatResponse(reply=reply, messages=messages)
