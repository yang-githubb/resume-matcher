import pytest
from pathlib import Path

from app.parsers.document import structure_text
from app.matching.keywords import overlap_score


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_structure_text_finds_python_skills():
    text = (FIXTURES / "sample_resume_strong.txt").read_text(encoding="utf-8")
    structured = structure_text(text)
    assert "python" in structured["skills"]
    assert "fastapi" in structured["skills"]
    assert "software engineer" in structured["titles"]


def test_overlap_score_matched_and_missing():
    resume_skills = ["python", "fastapi", "sql"]
    job_skills = ["python", "docker", "aws"]
    score, matched, missing = overlap_score(resume_skills, job_skills)
    assert score == pytest.approx(1 / 3)
    assert matched == ["python"]
    assert "docker" in missing
    assert "aws" in missing


def test_job_fixture_has_backend_skills():
    text = (FIXTURES / "sample_job.txt").read_text(encoding="utf-8")
    structured = structure_text(text)
    assert "python" in structured["skills"]
    assert "postgresql" in structured["skills"] or "sql" in structured["skills"]
