from __future__ import annotations

import httpx

from app.sources.base import FetchedJob, JobQuery, html_to_text

NAME = "jobicy"
LABEL = "Jobicy (remote jobs)"
REQUIRES_KEY = False
ENDPOINT = "https://jobicy.com/api/v2/remote-jobs"


def is_available() -> bool:
    return True


async def fetch(client: httpx.AsyncClient, query: JobQuery) -> list[FetchedJob]:
    params: dict[str, str | int] = {"count": min(max(query.limit, 20), 50)}
    if query.keywords.strip():
        params["tag"] = query.keywords.strip()

    response = await client.get(ENDPOINT, params=params)
    response.raise_for_status()
    payload = response.json()

    jobs: list[FetchedJob] = []
    for raw in payload.get("jobs", []):
        description = html_to_text(raw.get("jobDescription") or raw.get("jobExcerpt", ""))
        if not description:
            continue

        salary = None
        if raw.get("annualSalaryMin") and raw.get("annualSalaryMax"):
            currency = raw.get("salaryCurrency", "")
            salary = f"{raw['annualSalaryMin']}-{raw['annualSalaryMax']} {currency}".strip()

        jobs.append(
            FetchedJob(
                source=NAME,
                external_id=str(raw.get("id", "")),
                title=str(raw.get("jobTitle", "")).strip(),
                company=str(raw.get("companyName", "")).strip(),
                url=raw.get("url", ""),
                description=description,
                location=str(raw.get("jobGeo", "")).strip(),
                remote=True,
                posted_at=raw.get("pubDate"),
                salary=salary,
                tags=[t for t in raw.get("jobIndustry", []) if isinstance(t, str)],
            )
        )
    return jobs
