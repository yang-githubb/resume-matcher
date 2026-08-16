from __future__ import annotations

import httpx

from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "remotive"
LABEL = "Remotive (remote jobs)"
REQUIRES_KEY = False
ENDPOINT = "https://remotive.com/api/remote-jobs"


def is_available() -> bool:
    return True


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    params: dict[str, str | int] = {"limit": min(query.limit * 2, 100)}
    if query.keywords.strip():
        params["search"] = query.keywords.strip()

    response = await client.get(ENDPOINT, params=params)
    response.raise_for_status()
    payload = response.json()

    jobs: list[FetchedJob] = []
    for raw in payload.get("jobs", []):
        description = html_to_text(raw.get("description", ""))
        if not description:
            continue
        jobs.append(
            FetchedJob(
                source=NAME,
                external_id=str(raw.get("id", "")),
                title=raw.get("title", "").strip(),
                company=raw.get("company_name", "").strip(),
                url=raw.get("url", ""),
                description=description,
                location=raw.get("candidate_required_location", "").strip(),
                remote=True,
                posted_at=raw.get("publication_date"),
                salary=(raw.get("salary") or "").strip() or None,
                tags=[t for t in raw.get("tags", []) if isinstance(t, str)],
            )
        )
    return jobs
