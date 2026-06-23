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


def test_rank_without_ollama(client, monkeypatch):
    job = client.post(
        "/documents/text",
        json={
            "doc_type": "job",
            "text": "Python FastAPI SQL Docker Agile REST API engineer role with PostgreSQL.",
            "label": "job.txt",
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
        "/match/rank",
        json={
            "mode": "seeker",
            "job_id": job["id"],
            "resume_ids": [resume["id"]],
            "explain": True,
        },
    )
    assert rank.status_code == 200
    data = rank.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["score"] > 0
    assert data["results"][0]["explanation"] == "Test explanation"
    assert data["variant"] == "resumes_for_job"


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
    assert data["variant"] == "jobs_for_resume"
    assert len(data["results"]) == 2
    assert data["results"][0]["score"] >= data["results"][1]["score"]
    assert data["results"][0]["job_filename"] == "job-a.txt"
