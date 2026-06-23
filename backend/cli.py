from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app import db
from app.explain.ollama import generate_explanation
from app.matching.scorer import rank_resumes
from app.parsers.document import extract_text, structure_text


def parse_and_store(path: Path, doc_type: str) -> str:
    text = extract_text(path)
    structured = structure_text(text)
    return db.insert_document(doc_type, path.name, text, structured)


async def run_cli(job_path: Path, resume_paths: list[Path], explain: bool) -> None:
    db.init_db()
    job_id = parse_and_store(job_path, "job")
    job = db.get_document(job_id)
    assert job is not None

    resumes = []
    for resume_path in resume_paths:
        resume_id = parse_and_store(resume_path, "resume")
        resume = db.get_document(resume_id)
        if resume:
            resumes.append(resume)

    ranked = rank_resumes(resumes, job)
    print(f"\nJob: {job_path.name}\n{'=' * 40}")
    for index, item in enumerate(ranked, start=1):
        resume = item["resume"]
        print(f"\n#{index} {resume['filename']} — {item['score']}%")
        print(f"  semantic: {item['semantic_score']}% | keyword: {item['keyword_score']}%")
        print(f"  matched skills: {', '.join(item['breakdown']['matched_skills']) or 'none'}")
        print(f"  missing skills: {', '.join(item['breakdown']['missing_skills']) or 'none'}")

        if explain:
            print("\n  Analysis:")
            explanation = await generate_explanation(
                resume,
                job,
                item["breakdown"],
                {
                    "score": item["score"],
                    "semantic_score": item["semantic_score"],
                    "keyword_score": item["keyword_score"],
                },
            )
            for line in explanation.splitlines():
                print(f"  {line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank resumes against a job description.")
    parser.add_argument("--job", type=Path, required=True, help="Path to job PDF/DOCX")
    parser.add_argument("--resumes", type=Path, nargs="+", required=True, help="Resume files (max 2)")
    parser.add_argument("--no-explain", action="store_true", help="Skip Ollama explanation")
    args = parser.parse_args()

    if len(args.resumes) > 2:
        parser.error("At most 2 resumes are supported.")

    asyncio.run(run_cli(args.job, args.resumes, explain=not args.no_explain))


if __name__ == "__main__":
    main()
