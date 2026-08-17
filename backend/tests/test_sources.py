import pytest

from app.sources import adzuna, jsearch
from app.sources.base import FetchedJob, JobQuery, html_to_text
from app.sources.registry import _dedupe


def make_job(title: str, company: str = "Acme", description: str = "", **kwargs) -> FetchedJob:
    return FetchedJob(
        source=kwargs.pop("source", "test"),
        external_id=kwargs.pop("external_id", title.lower().replace(" ", "-")),
        title=title,
        company=company,
        url="https://example.com/job",
        description=description,
        **kwargs,
    )


def test_html_to_text_strips_tags_and_keeps_structure():
    html = "<p>We need a dev.</p><ul><li>Python</li><li>SQL</li></ul><script>x=1</script>"
    text = html_to_text(html)
    assert "We need a dev." in text
    assert "- Python" in text
    assert "x=1" not in text
    assert "<" not in text


def test_html_to_text_unescapes_entities():
    assert "R&D" in html_to_text("<p>R&amp;D team</p>")


def test_relevance_ranks_title_matches_above_body_mentions():
    query = JobQuery(keywords="python backend engineer")

    backend = make_job("Backend Engineer (Python)", description="APIs, docker")
    sales = make_job(
        "Inside Sales Contractor",
        description="Work with our engineer team to sell python-based tools",
    )

    assert backend.relevance(query) > sales.relevance(query)
    assert sales.relevance(query) < 0.3  # filtered out by the default threshold
    assert backend.relevance(query) >= 0.3


def test_relevance_is_one_when_no_terms_given():
    assert make_job("Anything").relevance(JobQuery(keywords="")) == 1.0


def test_dedupe_drops_same_posting_syndicated_across_boards():
    jobs = [
        make_job("Backend Engineer", "Acme", source="remotive", external_id="1"),
        make_job("Backend Engineer", "Acme", source="jobicy", external_id="2"),
        make_job("Frontend Engineer", "Acme", source="jobicy", external_id="3"),
    ]
    unique = _dedupe(jobs)
    assert len(unique) == 2
    assert unique[0].source == "remotive"  # first source wins


def test_document_text_leads_with_title_and_company():
    job = make_job("Backend Engineer", "Acme", description="Build APIs.")
    text = job.to_document_text()
    assert text.startswith("Backend Engineer")
    assert "Company: Acme" in text
    assert "Build APIs." in text


@pytest.mark.parametrize(
    "keywords,expected",
    [("python backend", ["python", "backend"]), ("a python b", ["python"])],
)
def test_query_terms_drops_single_characters(keywords: str, expected: list[str]):
    assert JobQuery(keywords=keywords).terms == expected


def test_adzuna_does_not_claim_malaysia_coverage():
    """A silent fallback would serve UK jobs to someone searching Malaysia."""
    assert "my" not in adzuna.COUNTRIES
    assert "sg" in adzuna.COUNTRIES


def test_jsearch_needs_a_key_to_be_available(monkeypatch):
    monkeypatch.setattr(jsearch.settings, "jsearch_api_key", "")
    assert jsearch.is_available() is False
    monkeypatch.setattr(jsearch.settings, "jsearch_api_key", "abc123")
    assert jsearch.is_available() is True


def test_jsearch_builds_location_from_parts_when_absent():
    assert jsearch._location({"job_location": "Kuala Lumpur, Malaysia"}) == "Kuala Lumpur, Malaysia"
    assert (
        jsearch._location({"job_city": "Penang", "job_state": None, "job_country": "MY"})
        == "Penang, MY"
    )


def test_jsearch_salary_needs_both_bounds():
    assert jsearch._salary({"job_min_salary": 1000}) is None
    assert (
        jsearch._salary(
            {
                "job_min_salary": 5000,
                "job_max_salary": 8000,
                "job_salary_currency": "MYR",
                "job_salary_period": "MONTH",
            }
        )
        == "5000-8000 MYR MONTH"
    )
