from __future__ import annotations

from typing import Any


def build_session_markdown(session: dict[str, Any], results: list[dict[str, Any]]) -> str:
    variant = "jobs_for_resume" if session.get("resume_id") and not session.get("job_id") else "resumes_for_job"

    lines = [
        "# Resume Match Report",
        "",
        f"- **Mode:** {session['mode']}",
        f"- **Session:** {session['id']}",
        f"- **Created:** {session['created_at']}",
        "",
        "## Rankings",
        "",
    ]

    for index, item in enumerate(results, start=1):
        if variant == "jobs_for_resume":
            title = item.get("job_filename", "Job")
        else:
            title = item.get("resume_filename", "Resume")

        lines.extend(
            [
                f"### #{index} {title} — {item['score']}%",
                "",
                f"- Semantic: {item['semantic_score']}%",
                f"- Keyword: {item['keyword_score']}%",
                f"- Matched skills: {', '.join(item['breakdown']['matched_skills']) or 'none'}",
                f"- Missing skills: {', '.join(item['breakdown']['missing_skills']) or 'none'}",
                "",
            ]
        )
        if item.get("explanation"):
            lines.extend(["#### Analysis", "", item["explanation"], ""])

    return "\n".join(lines).strip() + "\n"
