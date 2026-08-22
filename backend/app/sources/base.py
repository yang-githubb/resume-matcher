from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape

_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BLOCK_END_RE = re.compile(r"</(p|div|li|ul|ol|h[1-6]|tr|section)>", re.IGNORECASE)
_LI_RE = re.compile(r"<li[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(html: str) -> str:
    """Collapse an HTML job description into readable plain text.

    Job APIs return descriptions as HTML fragments. The matcher only ever sees
    text, so tags are stripped rather than parsed - no extra dependency needed.
    """
    if not html:
        return ""
    text = _SCRIPT_RE.sub(" ", html)
    text = _BR_RE.sub("\n", text)
    text = _LI_RE.sub("- ", text)
    text = _BLOCK_END_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass
class JobQuery:
    """What the user is looking for, normalised across every source."""

    keywords: str
    location: str | None = None
    remote_only: bool = False
    country: str = "gb"
    limit: int = 25
    # Postings below this relevance are dropped before the resume is scored.
    min_relevance: float = 0.3

    @property
    def terms(self) -> list[str]:
        return [t for t in re.split(r"[\s,]+", self.keywords.lower()) if len(t) > 1]


@dataclass
class FetchedJob:
    """A posting pulled from a remote board, before it becomes a document."""

    source: str
    external_id: str
    title: str
    company: str
    url: str
    description: str
    location: str = ""
    remote: bool = False
    posted_at: str | None = None
    salary: str | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Boards hand these back HTML-escaped ("H&amp;M"). Only the description
        # goes through html_to_text, so they are unescaped here instead - once,
        # rather than in every adapter.
        self.title = unescape(self.title).strip()
        self.company = unescape(self.company).strip()
        self.location = unescape(self.location).strip()

    @property
    def label(self) -> str:
        return f"{self.title} - {self.company or 'Unknown company'}"

    def to_document_text(self) -> str:
        """Build the text the embedder and keyword scorer will see.

        Title and company lead so the role signal is not drowned out by long
        boilerplate further down the posting.
        """
        header = [self.title.strip()]
        if self.company.strip():
            header.append(f"Company: {self.company.strip()}")
        if self.location.strip():
            header.append(f"Location: {self.location.strip()}")
        if self.remote:
            header.append("Remote: yes")
        if self.salary:
            header.append(f"Salary: {self.salary}")
        if self.tags:
            header.append(f"Tags: {', '.join(self.tags[:20])}")
        return "\n".join(header) + "\n\n" + self.description.strip()

    def relevance(self, query: JobQuery) -> float:
        """Score 0-1 for how well this posting answers the search terms.

        Weighted heavily toward the title: boards match loosely on free text,
        so a posting merely containing the word "engineer" somewhere in its
        body is not a backend engineering role.
        """
        terms = query.terms
        if not terms:
            return 1.0

        title = self.title.lower()
        body = " ".join([self.company, " ".join(self.tags), self.description[:3000]]).lower()

        title_hits = sum(1 for term in terms if term in title)
        body_hits = sum(1 for term in terms if term in body)

        return 0.7 * (title_hits / len(terms)) + 0.3 * (body_hits / len(terms))
