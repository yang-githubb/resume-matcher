import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "database_path", db_path)
    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    db.init_db()
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "embedding_model" in data
    assert "weights" in data


def test_create_job_from_text(client):
    response = client.post(
        "/documents/text",
        json={
            "doc_type": "job",
            "text": "Python developer needed. FastAPI, SQL, Docker, Agile experience required.",
            "label": "job.txt",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["doc_type"] == "job"
    assert "python" in body["structured"]["skills"]


@pytest.mark.parametrize("path", ["/match/rank", "/match/rank-jobs"])
def test_standalone_rank_endpoints_are_gone(client, path):
    """Searching is the only ranking entry point now."""
    assert client.post(path, json={"resume_id": "x"}).status_code == 404


def _fake_search(*jobs):
    from app.sources.registry import SearchOutcome, SourceOutcome

    async def run(_query, _sources=None):
        return SearchOutcome(
            jobs=list(jobs),
            sources=[SourceOutcome("remotive", "Remotive", len(jobs))],
        )

    return run


def test_discover_ranks_search_results_with_hand_added_jobs(client, monkeypatch):
    from app.sources.base import FetchedJob

    resume = client.post(
        "/documents/text",
        json={
            "doc_type": "resume",
            "text": "Software engineer with Python FastAPI SQL Docker Git Agile REST API experience.",
            "label": "resume.txt",
        },
    ).json()
    client.post(
        "/documents/text",
        json={
            "doc_type": "job",
            "text": "Python FastAPI SQL Docker Agile REST API engineer role with PostgreSQL.",
            "label": "hand-added.txt",
        },
    )

    fetched = FetchedJob(
        source="remotive",
        external_id="1",
        title="Marketing Coordinator",
        company="Acme",
        url="https://example.com/1",
        description="Social media, Excel, communication and content writing all day.",
    )

    async def fake_explain(*_args, **_kwargs):
        return "Test explanation"

    monkeypatch.setattr("app.routes.discover.registry.search", _fake_search(fetched))
    monkeypatch.setattr("app.routes.discover.generate_explanation", fake_explain)

    response = client.post(
        "/discover/match",
        json={
            "resume_id": resume["id"],
            "preferences": {"keywords": "python engineer"},
            "explain": False,
        },
    )
    assert response.status_code == 200
    data = response.json()

    names = [r["job_filename"] for r in data["results"]]
    assert "hand-added.txt" in names, "manual library jobs should be ranked too"
    assert "Marketing Coordinator - Acme" in names
    # The engineering job fits this resume better than the marketing one.
    assert names[0] == "hand-added.txt"


def test_discover_stream_reports_progress_then_results(client, monkeypatch):
    import json

    from app.sources.base import FetchedJob

    resume = client.post(
        "/documents/text",
        json={"doc_type": "resume", "text": "Python engineer with FastAPI and SQL.", "label": "r.txt"},
    ).json()

    fetched = FetchedJob(
        source="remotive",
        external_id="7",
        title="Backend Engineer",
        company="Acme",
        url="https://example.com/7",
        description="Python, FastAPI and SQL work on backend services.",
    )
    monkeypatch.setattr("app.routes.discover.registry.search", _fake_search(fetched))

    response = client.post(
        "/discover/match/stream",
        json={
            "resume_id": resume["id"],
            "preferences": {"keywords": "python engineer"},
            "explain": False,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = [
        json.loads(frame[len("data:") :].strip())
        for frame in response.text.split("\n\n")
        if frame.strip().startswith("data:")
    ]

    progress = [e["progress"] for e in events]
    assert progress == sorted(progress), "progress must never go backwards"
    assert progress[-1] == 1.0

    # Every frame but the last is progress; the last carries the payload.
    assert all("result" not in e for e in events[:-1])
    assert events[-1]["result"]["results"][0]["job_filename"] == "Backend Engineer - Acme"


def test_discover_stream_reports_failure_as_an_event(client, monkeypatch):
    import json

    response = client.post(
        "/discover/match/stream",
        json={"resume_id": "does-not-exist", "preferences": {"keywords": "python"}},
    )
    # The stream has already begun, so the failure arrives in-band rather than
    # as a status code.
    assert response.status_code == 200
    last = json.loads(response.text.strip().split("data:")[-1].strip())
    assert last["error"] == "Resume not found."


def test_discover_can_skip_the_library(client, monkeypatch):
    from app.sources.base import FetchedJob

    resume = client.post(
        "/documents/text",
        json={"doc_type": "resume", "text": "Python engineer with FastAPI and SQL.", "label": "r.txt"},
    ).json()
    client.post(
        "/documents/text",
        json={"doc_type": "job", "text": "Python FastAPI SQL engineer wanted here.", "label": "hand.txt"},
    )

    fetched = FetchedJob(
        source="remotive",
        external_id="9",
        title="Backend Engineer",
        company="Beta",
        url="https://example.com/9",
        description="Python, FastAPI and SQL work on backend services.",
    )
    monkeypatch.setattr("app.routes.discover.registry.search", _fake_search(fetched))

    response = client.post(
        "/discover/match",
        json={
            "resume_id": resume["id"],
            "preferences": {"keywords": "python engineer"},
            "explain": False,
            "include_library": False,
        },
    )
    assert response.status_code == 200
    names = [r["job_filename"] for r in response.json()["results"]]
    assert names == ["Backend Engineer - Beta"]


def test_only_the_newest_sessions_are_kept(client):
    from app import db

    resume = client.post(
        "/documents/text",
        json={
            "doc_type": "resume",
            "text": "Software engineer with Python FastAPI SQL Docker Git Agile REST API experience.",
            "label": "resume.txt",
        },
    ).json()

    created = [db.create_match_session(resume_id=resume["id"]) for _ in range(8)]

    sessions = client.get("/sessions").json()
    assert len(sessions) == db.MAX_SAVED_SESSIONS

    # The survivors are the most recent ones, oldest first dropped.
    kept = {s["id"] for s in sessions}
    assert kept == set(created[-db.MAX_SAVED_SESSIONS :])
