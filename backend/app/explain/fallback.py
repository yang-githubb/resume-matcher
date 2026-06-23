from __future__ import annotations

from typing import Any


def fallback_explanation(
    breakdown: dict[str, Any],
    scores: dict[str, float],
) -> str:
    matched = breakdown.get("matched_skills", [])
    missing = breakdown.get("missing_skills", [])

    strength_lines = [f"- Strong match on {skill}" for skill in matched[:6]]
    if not strength_lines:
        strength_lines = ["- Limited explicit skill overlap detected"]

    gap_lines = [f"- Job asks for {skill}" for skill in missing[:6]]
    if not gap_lines:
        gap_lines = ["- No major skill gaps detected from keyword list"]

    lines = [
        f"Overall fit: {scores['score']}% (semantic {scores['semantic_score']}%, keyword {scores['keyword_score']}%).",
        "",
        "Strengths:",
        *strength_lines,
        "",
        "Gaps:",
        *gap_lines,
        "",
        "Recommendations:",
        "- Highlight matched experience prominently in your resume summary.",
        "- Address top missing skills if you have related experience under different wording.",
        "",
        "(Ollama was unavailable — this is a rule-based summary. Start Ollama for AI analysis.)",
    ]
    return "\n".join(lines)
