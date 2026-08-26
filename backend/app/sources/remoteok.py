from __future__ import annotations

import httpx

from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "remoteok"
LABEL = "RemoteOK (remote jobs)"
REQUIRES_KEY = False
# These boards list remote roles worldwide and expose no geographic filter,
# so a city or country would be silently ignored.
SUPPORTS_LOCATION = False
SUPPORTS_COUNTRY = False
COUNTRIES: frozenset[str] | None = None
ENDPOINT = "https://remoteok.com/api"


def is_available() -> bool:
    return True


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    response = await client.get(ENDPOINT)
    response.raise_for_status()
    payload = response.json()

    jobs: list[FetchedJob] = []
    for raw in payload:
        # The first element of the feed is a legal notice, not a posting.
        if not isinstance(raw, dict) or not raw.get("position"):
            continue
        description = html_to_text(raw.get("description", ""))
        if not description:
            continue

        salary = None
        if raw.get("salary_min") and raw.get("salary_max"):
            salary = f"{raw['salary_min']}-{raw['salary_max']}"

        # This feed has no server-side search; the registry filters by relevance.
        jobs.append(
            FetchedJob(
                source=NAME,
                external_id=str(raw.get("id") or raw.get("slug", "")),
                title=str(raw.get("position", "")).strip(),
                company=str(raw.get("company", "")).strip(),
                url=raw.get("url") or raw.get("apply_url", ""),
                description=description,
                location=str(raw.get("location", "")).strip(),
                remote=True,
                posted_at=raw.get("date"),
                salary=salary,
                tags=[t for t in raw.get("tags", []) if isinstance(t, str)],
            )
        )
    return jobs
