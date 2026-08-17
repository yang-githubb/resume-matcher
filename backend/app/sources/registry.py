from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import httpx

from app.sources import adzuna, arbeitnow, jobicy, jsearch, remoteok, remotive
from app.sources.base import FetchedJob, JobQuery

# Order matters only for tie-breaking during dedupe: earlier sources win.
# JSearch leads because it carries the original posting's apply link.
MODULES = [jsearch, remotive, remoteok, arbeitnow, jobicy, adzuna]
BY_NAME = {module.NAME: module for module in MODULES}

REQUEST_TIMEOUT = 20.0
# Job boards reject unidentified clients; identify the app honestly.
USER_AGENT = "resume-matcher/1.0 (local job matching tool)"


@dataclass
class SourceOutcome:
    name: str
    label: str
    fetched: int
    error: str | None = None


@dataclass
class SearchOutcome:
    jobs: list[FetchedJob]
    sources: list[SourceOutcome]


def available_sources() -> list[dict[str, object]]:
    return [
        {
            "name": module.NAME,
            "label": module.LABEL,
            "requires_key": module.REQUIRES_KEY,
            "available": module.is_available(),
        }
        for module in MODULES
    ]


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _dedupe(jobs: list[FetchedJob]) -> list[FetchedJob]:
    """Drop repeats within and across sources.

    The same posting is often syndicated to several boards, so identity falls
    back to (title, company) once the per-source id has been checked.
    """
    seen_ids: set[tuple[str, str]] = set()
    seen_pairs: set[tuple[str, str]] = set()
    unique: list[FetchedJob] = []

    for job in jobs:
        id_key = (job.source, job.external_id)
        pair_key = (_normalise(job.title), _normalise(job.company))
        if job.external_id and id_key in seen_ids:
            continue
        if pair_key in seen_pairs and all(pair_key):
            continue
        seen_ids.add(id_key)
        seen_pairs.add(pair_key)
        unique.append(job)

    return unique


async def _run_source(module, client: httpx.AsyncClient, query: JobQuery) -> tuple[SourceOutcome, list[FetchedJob]]:
    if not module.is_available():
        return (
            SourceOutcome(module.NAME, module.LABEL, 0, "Not configured - add an API key."),
            [],
        )
    try:
        jobs = await module.fetch(client, query)
    except httpx.HTTPStatusError as exc:
        return SourceOutcome(module.NAME, module.LABEL, 0, f"HTTP {exc.response.status_code}"), []
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return SourceOutcome(module.NAME, module.LABEL, 0, str(exc)[:200]), []
    return SourceOutcome(module.NAME, module.LABEL, len(jobs)), jobs


async def search(query: JobQuery, sources: list[str] | None = None) -> SearchOutcome:
    """Query every selected board concurrently; a failing board is skipped, not fatal."""
    selected = [BY_NAME[name] for name in sources if name in BY_NAME] if sources else MODULES
    if not selected:
        selected = MODULES

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(*(_run_source(m, client, query) for m in selected))

    outcomes = [outcome for outcome, _ in results]
    jobs: list[FetchedJob] = []
    for _, source_jobs in results:
        jobs.extend(source_jobs)

    if query.remote_only:
        jobs = [job for job in jobs if job.remote]

    jobs = _dedupe(jobs)

    # Boards match free text loosely, so relevance is enforced here rather than
    # trusting each source's own search. Keep the strongest candidates, and fall
    # back to the best available if the bar excludes everything.
    scored = sorted(
        ((job.relevance(query), job) for job in jobs),
        key=lambda pair: pair[0],
        reverse=True,
    )
    relevant = [job for score, job in scored if score >= query.min_relevance]
    if not relevant:
        relevant = [job for _, job in scored]

    return SearchOutcome(jobs=relevant[: query.limit], sources=outcomes)
