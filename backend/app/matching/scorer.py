from __future__ import annotations

from typing import Any

import numpy as np

from app.config import settings
from app.matching.embedder import cosine_similarity, embed_text
from app.matching.keywords import overlap_score


def hybrid_score(resume: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    resume_struct = resume["structured"]
    job_struct = job["structured"]

    resume_vec = embed_text(resume["raw_text"])
    job_vec = embed_text(job["raw_text"])
    semantic = cosine_similarity(resume_vec, job_vec)

    skill_score, matched_skills, missing_skills = overlap_score(
        resume_struct.get("skills", []),
        job_struct.get("skills", []),
    )
    keyword_score, matched_keywords, missing_keywords = overlap_score(
        resume_struct.get("keywords", []),
        job_struct.get("keywords", []),
    )
    keyword_blend = 0.6 * skill_score + 0.4 * keyword_score

    total = settings.semantic_weight * semantic + settings.keyword_weight * keyword_blend
    score_100 = round(total * 100, 1)

    return {
        "score": score_100,
        "semantic_score": round(semantic * 100, 1),
        "keyword_score": round(keyword_blend * 100, 1),
        "breakdown": {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_keywords": matched_keywords[:15],
            "missing_keywords": missing_keywords[:15],
        },
    }


def rank_jobs(jobs: list[dict[str, Any]], resume: dict[str, Any]) -> list[dict[str, Any]]:
    scored = []
    for job in jobs:
        result = hybrid_score(resume, job)
        scored.append({"job": job, **result})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored
