from __future__ import annotations

import asyncio
import math

import httpx

from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "themuse"
LABEL = "The Muse (onsite + remote, no key)"
REQUIRES_KEY = False

# The only keyless source with real geography: the others list remote roles
# worldwide and cannot narrow by country at all.
SUPPORTS_LOCATION = False
SUPPORTS_COUNTRY = True
# Verified by querying each country and checking the postings really come back
# from it. The API silently ignores a location it does not recognise and
# returns unfiltered results, so an unverified country would look like it
# worked while quietly serving jobs from anywhere.
COUNTRIES: frozenset[str] | None = frozenset(
    {"us", "gb", "de", "fr", "nl", "es", "it", "be", "pl"}
)

ENDPOINT = "https://www.themuse.com/api/public/jobs"
PAGE_SIZE = 20
MAX_PAGES = 3

# Filtering is per city, not per country, so each country is covered by the
# cities confirmed to return their own postings. Barcelona, Rome and Vienna
# were tried and silently ignored, which is why they are absent.
CITIES: dict[str, list[str]] = {
    "us": ["New York, NY", "San Francisco, CA"],
    "gb": ["London, United Kingdom"],
    "de": ["Berlin, Germany", "Munich, Germany"],
    "fr": ["Paris, France"],
    "nl": ["Amsterdam, Netherlands"],
    "es": ["Madrid, Spain"],
    "it": ["Milan, Italy"],
    "be": ["Brussels, Belgium"],
    "pl": ["Warsaw, Poland", "Krakow, Poland"],
}

# There is no free-text search, so keywords are steered into a category
# instead. Only categories with real volume are worth mapping; the rest come
# back empty and would return nothing at all.
CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("software", "developer", "backend", "frontend", "full stack", "fullstack",
      "engineer", "programming", "devops", "sre", "platform"), "Software Engineering"),
    (("data", "analytics", "analyst", "machine learning", "ml", "scientist"),
     "Data and Analytics"),
    (("design", "ux", "ui", "product design"), "Design and UX"),
    (("product manager", "product management"), "Product Management"),
    (("project", "programme", "program manager", "scrum"), "Project Management"),
    (("sales", "account executive", "business development"), "Sales"),
    (("support", "customer success", "customer service"), "Customer Service"),
    (("operations", "business operations", "strategy"), "Business Operations"),
]


def is_available() -> bool:
    return True


def _category(keywords: str) -> str | None:
    """Map free-text keywords onto a category the API recognises."""
    text = keywords.lower()
    for terms, category in CATEGORIES:
        if any(term in text for term in terms):
            return category
    return None


def _locations(country: str) -> list[str]:
    return CITIES.get(country.lower(), [])


def _parse(raw: dict) -> FetchedJob | None:
    description = html_to_text(raw.get("contents", ""))
    if not description:
        return None

    names = [loc.get("name", "") for loc in raw.get("locations", []) if loc.get("name")]
    # A posting can list several places; "Flexible / Remote" is how the API
    # marks one that is not tied to an office.
    remote = any("remote" in name.lower() or "flexible" in name.lower() for name in names)
    onsite = [name for name in names if "remote" not in name.lower() and "flexible" not in name.lower()]

    refs = raw.get("refs") or {}
    return FetchedJob(
        source=NAME,
        external_id=str(raw.get("id", "")),
        title=(raw.get("name") or "").strip(),
        company=((raw.get("company") or {}).get("name") or "").strip(),
        url=refs.get("landing_page", ""),
        description=description,
        location="Remote" if remote else ", ".join(onsite[:2]),
        remote=remote,
        posted_at=raw.get("publication_date"),
        tags=[level.get("name", "") for level in raw.get("levels", []) if level.get("name")],
    )


async def _page(client: httpx.AsyncClient, params: list[tuple[str, str]], page: int) -> list[dict]:
    response = await client.get(ENDPOINT, params=[*params, ("page", str(page))])
    response.raise_for_status()
    return response.json().get("results", [])


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    locations = _locations(query.country)
    if not locations:
        # Better to return nothing than to send a location the API will ignore
        # while handing back jobs from everywhere.
        return []

    # httpx takes repeated params as a list of pairs; the API ORs them.
    params: list[tuple[str, str]] = [("location", city) for city in locations]
    category = _category(query.keywords)
    if category:
        params.append(("category", category))

    pages = min(max(math.ceil(query.limit / PAGE_SIZE), 1), MAX_PAGES)
    batches = await asyncio.gather(
        *(_page(client, params, page) for page in range(pages)),
        return_exceptions=True,
    )

    jobs: list[FetchedJob] = []
    for batch in batches:
        if isinstance(batch, BaseException):
            continue
        for raw in batch:
            job = _parse(raw)
            if job is not None:
                jobs.append(job)
    return jobs
