from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app import db
from app.explain.ollama import generate_explanation
from app.matching.scorer import rank_jobs
from app.parsers.document import extract_text, structure_text


def parse_and_store(path: Path, doc_type: str) -> str:
    text = extract_text(path)
    structured = structure_text(text)
    return db.insert_document(doc_type, path.name, text, structured)


async def run_cli(resume_path: Path, job_paths: list[Path], explain: bool) -> None:
    db.init_db()
    resume_id = parse_and_store(resume_path, "resume")
    resume = db.get_document(resume_id)
    assert resume is not None

    jobs = []
    for job_path in job_paths:
        job_id = parse_and_store(job_path, "job")
        job = db.get_document(job_id)
        if job:
            jobs.append(job)

    ranked = rank_jobs(jobs, resume)
    print(f"\nResume: {resume_path.name}\n{'=' * 40}")
    for index, item in enumerate(ranked, start=1):
        job = item["job"]
        print(f"\n#{index} {job['filename']} — {item['score']}%")
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
    parser = argparse.ArgumentParser(description="Rank job descriptions against a resume.")
    parser.add_argument("--resume", type=Path, required=True, help="Path to resume PDF/DOCX/TXT")
    parser.add_argument("--jobs", type=Path, nargs="+", required=True, help="Job description files")
    parser.add_argument("--no-explain", action="store_true", help="Skip Ollama explanation")
    args = parser.parse_args()

    asyncio.run(run_cli(args.resume, args.jobs, explain=not args.no_explain))


if __name__ == "__main__":
    main()
