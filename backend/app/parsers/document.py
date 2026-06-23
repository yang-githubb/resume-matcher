from __future__ import annotations

import re
from pathlib import Path

import fitz
from docx import Document

SKILL_PATTERNS = re.compile(
    r"\b(python|java|javascript|typescript|react|node\.?js|sql|aws|azure|gcp|docker|"
    r"kubernetes|git|ci/cd|agile|scrum|fastapi|django|flask|rest|api|machine learning|"
    r"deep learning|nlp|data analysis|pandas|numpy|tensorflow|pytorch|linux|html|css|"
    r"postgresql|mongodb|redis|kafka|spark|tableau|power bi|excel|leadership|communication)\b",
    re.IGNORECASE,
)

TITLE_PATTERNS = re.compile(
    r"\b(software engineer|developer|analyst|manager|architect|intern|consultant|"
    r"data scientist|product manager|designer|devops|full[- ]?stack|backend|frontend)\b",
    re.IGNORECASE,
)


def extract_text_from_pdf(path: Path) -> str:
    doc = fitz.open(path)
    try:
        parts = [page.get_text("text") for page in doc]
    finally:
        doc.close()
    return "\n".join(parts).strip()


def extract_text_from_docx(path: Path) -> str:
    document = Document(path)
    return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8").strip()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in {".docx", ".doc"}:
        if suffix == ".doc":
            raise ValueError("Legacy .doc is not supported. Save as .docx or PDF.")
        return extract_text_from_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def structure_text(text: str) -> dict[str, list[str]]:
    lowered = text.lower()
    skills = sorted({m.group(0).lower() for m in SKILL_PATTERNS.finditer(lowered)})
    titles = sorted({m.group(0).lower() for m in TITLE_PATTERNS.finditer(lowered)})

    words = re.findall(r"[a-z][a-z0-9+#./-]{2,}", lowered)
    freq: dict[str, int] = {}
    for word in words:
        freq[word] = freq.get(word, 0) + 1
    keywords = [w for w, _ in sorted(freq.items(), key=lambda item: (-item[1], item[0]))[:40]]

    return {"skills": skills, "titles": titles, "keywords": keywords}
