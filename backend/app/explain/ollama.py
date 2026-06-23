from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

ANALYSIS_PROMPT = """You are a resume matching assistant. Analyze how well the resume fits the job.
Use only facts from the provided texts and match breakdown. Be concise and specific.

Respond in this JSON shape only:
{
  "fit_summary": "2-3 sentences",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "recommendations": ["...", "..."]
}
"""

CHAT_PROMPT = """You answer follow-up questions about a resume vs job match.
Ground every answer in the resume text, job text, and match breakdown.
If the user asks something not supported by the documents, say you cannot tell from the uploaded files.
Keep answers concise (under 150 words unless asked for detail).
"""


async def _ollama_chat(messages: list[dict[str, str]]) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("message", {}).get("content", "").strip()


def _format_match_context(
    resume: dict[str, Any],
    job: dict[str, Any],
    breakdown: dict[str, Any],
    scores: dict[str, float],
) -> str:
    return (
        f"Scores: overall={scores['score']}, semantic={scores['semantic_score']}, "
        f"keyword={scores['keyword_score']}\n"
        f"Matched skills: {', '.join(breakdown.get('matched_skills', [])) or 'none'}\n"
        f"Missing skills: {', '.join(breakdown.get('missing_skills', [])) or 'none'}\n"
        f"Matched keywords: {', '.join(breakdown.get('matched_keywords', [])) or 'none'}\n"
        f"Missing keywords: {', '.join(breakdown.get('missing_keywords', [])) or 'none'}\n\n"
        f"JOB ({job['filename']}):\n{job['raw_text'][:4000]}\n\n"
        f"RESUME ({resume['filename']}):\n{resume['raw_text'][:4000]}"
    )


async def generate_explanation(
    resume: dict[str, Any],
    job: dict[str, Any],
    breakdown: dict[str, Any],
    scores: dict[str, float],
) -> str:
    from app.explain.fallback import fallback_explanation

    try:
        context = _format_match_context(resume, job, breakdown, scores)
        messages = [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": context},
        ]
        raw = await _ollama_chat(messages)

        try:
            parsed = json.loads(raw)
            lines = [
                parsed.get("fit_summary", ""),
                "",
                "Strengths:",
                *[f"- {s}" for s in parsed.get("strengths", [])],
                "",
                "Gaps:",
                *[f"- {g}" for g in parsed.get("gaps", [])],
                "",
                "Recommendations:",
                *[f"- {r}" for r in parsed.get("recommendations", [])],
            ]
            return "\n".join(line for line in lines if line is not None).strip()
        except json.JSONDecodeError:
            return raw
    except httpx.HTTPError:
        return fallback_explanation(breakdown, scores)


async def chat_about_match(
    resume: dict[str, Any],
    job: dict[str, Any],
    breakdown: dict[str, Any],
    scores: dict[str, float],
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    context = _format_match_context(resume, job, breakdown, scores)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": CHAT_PROMPT},
        {"role": "user", "content": f"Context:\n{context}"},
    ]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})
    try:
        return await _ollama_chat(messages)
    except httpx.HTTPError as exc:
        return (
            "Ollama is not reachable. Start it with `ollama serve` and ensure "
            f"`{settings.ollama_model}` is pulled. ({exc.__class__.__name__})"
        )


async def check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False
