from __future__ import annotations

import math

import httpx

from app.config import settings
from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "jsearch"
LABEL = "JSearch / Google for Jobs (needs free RapidAPI key)"
REQUIRES_KEY = True
# Google for Jobs is worldwide, and takes both a country code and a free-text
# place folded into the query, so COUNTRIES is None meaning "any".
SUPPORTS_LOCATION = True
SUPPORTS_COUNTRY = True
COUNTRIES: frozenset[str] | None = None
ENDPOINT = "https://jsearch.p.rapidapi.com/search"
HOST = "jsearch.p.rapidapi.com"

# Each page returns ~10 jobs and counts as one request against the free tier,
# so pages are capped well below the 50-job ceiling the UI allows.
JOBS_PER_PAGE = 10
MAX_PAGES = 3


def is_available() -> bool:
    return bool(settings.jsearch_api_key)


def _salary(raw: dict) -> str | None:
    low, high = raw.get("job_min_salary"), raw.get("job_max_salary")
    if not low or not high:
        return None
    currency = raw.get("job_salary_currency") or ""
    period = raw.get("job_salary_period") or ""
    return f"{int(low)}-{int(high)} {currency} {period}".strip()


def _location(raw: dict) -> str:
    if raw.get("job_location"):
        return str(raw["job_location"]).strip()
    parts = [raw.get("job_city"), raw.get("job_state"), raw.get("job_country")]
    return ", ".join(str(p) for p in parts if p)


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    if not is_available():
        return []

    # JSearch takes one free-text query; folding the location in beats the
    # separate filter, which is strict about exact place names.
    search = query.keywords.strip()
    if query.location and query.location.strip():
        search = f"{search} in {query.location.strip()}"

    params: dict[str, str | int] = {
        "query": search,
        "page": 1,
        "num_pages": min(max(1, math.ceil(query.limit / JOBS_PER_PAGE)), MAX_PAGES),
        "country": query.country.lower(),
    }
    if query.remote_only:
        params["work_from_home"] = "true"

    response = await client.get(
        ENDPOINT,
        params=params,
        headers={"X-RapidAPI-Key": settings.jsearch_api_key, "X-RapidAPI-Host": HOST},
    )
    response.raise_for_status()
    payload = response.json()

    jobs: list[FetchedJob] = []
    for raw in payload.get("data", []):
        description = html_to_text(raw.get("job_description", ""))
        if not description:
            continue

        jobs.append(
            FetchedJob(
                source=NAME,
                external_id=str(raw.get("job_id", "")),
                title=str(raw.get("job_title", "")).strip(),
                company=str(raw.get("employer_name") or "").strip(),
                url=raw.get("job_apply_link") or raw.get("job_google_link", ""),
                description=description,
                location=_location(raw),
                remote=bool(raw.get("job_is_remote")),
                posted_at=raw.get("job_posted_at_datetime_utc"),
                salary=_salary(raw),
                # The publisher (LinkedIn, Indeed, JobStreet...) is useful context.
                tags=[t for t in [raw.get("job_publisher"), raw.get("job_employment_type")] if t],
            )
        )
    return jobs
