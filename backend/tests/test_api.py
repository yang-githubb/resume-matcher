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


def test_recruiter_rank_endpoint_is_gone(client):
    response = client.post(
        "/match/rank",
        json={"mode": "recruiter", "job_id": "x", "resume_ids": ["y"], "explain": False},
    )
    assert response.status_code == 404


def test_rank_jobs_for_resume(client, monkeypatch):
    job_a = client.post(
        "/documents/text",
        json={
            "doc_type": "job",
            "text": "Python FastAPI SQL Docker Agile REST API engineer role with PostgreSQL.",
            "label": "job-a.txt",
        },
    ).json()
    job_b = client.post(
        "/documents/text",
        json={
            "doc_type": "job",
            "text": "Marketing coordinator social media Excel communication content writing.",
            "label": "job-b.txt",
        },
    ).json()
    resume = client.post(
        "/documents/text",
        json={
            "doc_type": "resume",
            "text": "Software engineer with Python FastAPI SQL Docker Git Agile REST API experience.",
            "label": "resume.txt",
        },
    ).json()

    async def fake_explain(*_args, **_kwargs):
        return "Test explanation"

    monkeypatch.setattr("app.routes.match.generate_explanation", fake_explain)

    rank = client.post(
        "/match/rank-jobs",
        json={"resume_id": resume["id"], "job_ids": [job_a["id"], job_b["id"]], "explain": True},
    )
    assert rank.status_code == 200
    data = rank.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["score"] >= data["results"][1]["score"]
    assert data["results"][0]["job_filename"] == "job-a.txt"


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
