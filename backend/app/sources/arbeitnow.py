from __future__ import annotations

import httpx

from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "arbeitnow"
LABEL = "Arbeitnow (EU jobs)"
REQUIRES_KEY = False
ENDPOINT = "https://www.arbeitnow.com/api/job-board-api"


def is_available() -> bool:
    return True


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    response = await client.get(ENDPOINT)
    response.raise_for_status()
    payload = response.json()

    jobs: list[FetchedJob] = []
    for raw in payload.get("data", []):
        description = html_to_text(raw.get("description", ""))
        if not description:
            continue

        # This feed has no server-side search; the registry filters by relevance.
        jobs.append(
            FetchedJob(
                source=NAME,
                external_id=str(raw.get("slug", "")),
                title=str(raw.get("title", "")).strip(),
                company=str(raw.get("company_name", "")).strip(),
                url=raw.get("url", ""),
                description=description,
                location=str(raw.get("location", "")).strip(),
                remote=bool(raw.get("remote")),
                posted_at=str(raw.get("created_at", "")) or None,
                tags=[t for t in raw.get("tags", []) if isinstance(t, str)],
            )
        )
    return jobs
