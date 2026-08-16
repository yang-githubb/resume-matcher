from __future__ import annotations

import httpx

from app.config import settings
from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "adzuna"
LABEL = "Adzuna (onsite + remote, needs free API key)"
REQUIRES_KEY = True
ENDPOINT = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

# Countries Adzuna serves; anything else falls back to gb.
COUNTRIES = {
    "gb", "us", "au", "at", "be", "br", "ca", "ch", "de", "es",
    "fr", "in", "it", "mx", "nl", "nz", "pl", "sg", "za",
}


def is_available() -> bool:
    return bool(settings.adzuna_app_id and settings.adzuna_app_key)


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    if not is_available():
        return []

    country = query.country.lower() if query.country.lower() in COUNTRIES else "gb"
    params: dict[str, str | int] = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": min(max(query.limit, 10), 50),
        "content-type": "application/json",
    }
    if query.keywords.strip():
        params["what"] = query.keywords.strip()
    if query.location and query.location.strip():
        params["where"] = query.location.strip()

    response = await client.get(ENDPOINT.format(country=country), params=params)
    response.raise_for_status()
    payload = response.json()

    jobs: list[FetchedJob] = []
    for raw in payload.get("results", []):
        description = html_to_text(raw.get("description", ""))
        if not description:
            continue

        salary = None
        if raw.get("salary_min") and raw.get("salary_max"):
            salary = f"{int(raw['salary_min'])}-{int(raw['salary_max'])}"

        location = (raw.get("location") or {}).get("display_name", "")
        jobs.append(
            FetchedJob(
                source=NAME,
                external_id=str(raw.get("id", "")),
                title=str(raw.get("title", "")).strip(),
                company=str((raw.get("company") or {}).get("display_name", "")).strip(),
                url=raw.get("redirect_url", ""),
                description=description,
                location=str(location).strip(),
                remote="remote" in f"{raw.get('title', '')} {location}".lower(),
                posted_at=raw.get("created"),
                salary=salary,
            )
        )
    return jobs
