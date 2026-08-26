from __future__ import annotations

import httpx

from app.config import settings
from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "adzuna"
LABEL = "Adzuna (onsite + remote, needs free API key)"
REQUIRES_KEY = True
ENDPOINT = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

# The 18 countries Adzuna serves. Notably absent: Malaysia and most of
# South East Asia apart from Singapore.
# Adzuna is per-country: the code goes in the URL, so an uncovered country
# has no endpoint at all rather than simply returning nothing.
SUPPORTS_LOCATION = True
SUPPORTS_COUNTRY = True
COUNTRIES: frozenset[str] | None = frozenset({
    "gb", "us", "au", "at", "be", "br", "ca", "de", "es",
    "fr", "in", "it", "mx", "nl", "nz", "pl", "sg", "za",
})


class UnsupportedCountry(ValueError):
    """Raised so the search reports the gap instead of silently using another country."""


def is_available() -> bool:
    return bool(settings.adzuna_app_id and settings.adzuna_app_key)


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    if not is_available():
        return []

    country = query.country.lower()
    if country not in COUNTRIES:
        raise UnsupportedCountry(
            f"Adzuna has no {country.upper()} listings - it covers "
            f"{len(COUNTRIES)} countries, not including this one."
        )
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
