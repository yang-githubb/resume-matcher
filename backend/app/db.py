from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, sqlite3.Row]:
    return {row[1]: row for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _recreate_match_sessions(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE match_sessions_new (
            id TEXT PRIMARY KEY,
            mode TEXT NOT NULL CHECK (mode IN ('seeker', 'recruiter')),
            job_id TEXT,
            resume_id TEXT,
            created_at TEXT NOT NULL
        );
        INSERT INTO match_sessions_new (id, mode, job_id, resume_id, created_at)
        SELECT id, mode, job_id, resume_id, created_at FROM match_sessions;
        DROP TABLE match_sessions;
        ALTER TABLE match_sessions_new RENAME TO match_sessions;
        """
    )


def _migrate(conn: sqlite3.Connection) -> None:
    session_cols = _table_columns(conn, "match_sessions")

    if "resume_id" not in session_cols:
        conn.execute("ALTER TABLE match_sessions ADD COLUMN resume_id TEXT")
        session_cols = _table_columns(conn, "match_sessions")

    job_id_col = session_cols.get("job_id")
    if job_id_col is not None and job_id_col[3] == 1:
        _recreate_match_sessions(conn)

    result_cols = _table_columns(conn, "match_results")
    if "job_id" not in result_cols:
        conn.execute("ALTER TABLE match_results ADD COLUMN job_id TEXT")

    # Discovered jobs carry provenance so results can link back to the posting.
    doc_cols = _table_columns(conn, "documents")
    for column, ddl in (
        ("origin", "ALTER TABLE documents ADD COLUMN origin TEXT NOT NULL DEFAULT 'manual'"),
        ("source", "ALTER TABLE documents ADD COLUMN source TEXT"),
        ("external_id", "ALTER TABLE documents ADD COLUMN external_id TEXT"),
        ("url", "ALTER TABLE documents ADD COLUMN url TEXT"),
        ("company", "ALTER TABLE documents ADD COLUMN company TEXT"),
        ("location", "ALTER TABLE documents ADD COLUMN location TEXT"),
    ):
        if column not in doc_cols:
            conn.execute(ddl)

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_external
        ON documents(source, external_id)
        WHERE source IS NOT NULL AND external_id IS NOT NULL
        """
    )


def init_db() -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                doc_type TEXT NOT NULL CHECK (doc_type IN ('resume', 'job')),
                filename TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                structured_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS match_sessions (
                id TEXT PRIMARY KEY,
                mode TEXT NOT NULL CHECK (mode IN ('seeker', 'recruiter')),
                job_id TEXT,
                resume_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES documents(id),
                FOREIGN KEY (resume_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS match_results (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                resume_id TEXT,
                job_id TEXT,
                score REAL NOT NULL,
                semantic_score REAL NOT NULL,
                keyword_score REAL NOT NULL,
                breakdown_json TEXT NOT NULL,
                explanation TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES match_sessions(id),
                FOREIGN KEY (resume_id) REFERENCES documents(id),
                FOREIGN KEY (job_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES match_sessions(id)
            );
            """
        )
        _migrate(conn)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_document(
    doc_type: str,
    filename: str,
    raw_text: str,
    structured: dict[str, Any],
    *,
    origin: str = "manual",
    source: str | None = None,
    external_id: str | None = None,
    url: str | None = None,
    company: str | None = None,
    location: str | None = None,
) -> str:
    doc_id = str(uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents
            (id, doc_type, filename, raw_text, structured_json, created_at,
             origin, source, external_id, url, company, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                doc_type,
                filename,
                raw_text,
                json.dumps(structured),
                _utc_now(),
                origin,
                source,
                external_id,
                url,
                company,
                location,
            ),
        )
    return doc_id


def find_job_by_external(source: str, external_id: str) -> str | None:
    """Return an existing document id for a posting already pulled from a board."""
    if not source or not external_id:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM documents WHERE source = ? AND external_id = ?",
            (source, external_id),
        ).fetchone()
    return row["id"] if row else None


def get_document(doc_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "doc_type": row["doc_type"],
        "filename": row["filename"],
        "raw_text": row["raw_text"],
        "structured": json.loads(row["structured_json"]),
        "created_at": row["created_at"],
    }


def create_match_session(
    mode: str,
    job_id: str | None = None,
    resume_id: str | None = None,
) -> str:
    session_id = str(uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO match_sessions (id, mode, job_id, resume_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, mode, job_id, resume_id, _utc_now()),
        )
    return session_id


def insert_match_result(
    session_id: str,
    score: float,
    semantic_score: float,
    keyword_score: float,
    breakdown: dict[str, Any],
    resume_id: str | None = None,
    job_id: str | None = None,
    explanation: str | None = None,
) -> str:
    result_id = str(uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO match_results
            (id, session_id, resume_id, job_id, score, semantic_score, keyword_score, breakdown_json, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                session_id,
                resume_id,
                job_id,
                score,
                semantic_score,
                keyword_score,
                json.dumps(breakdown),
                explanation,
                _utc_now(),
            ),
        )
    return result_id


def get_session_results(session_id: str) -> list[dict[str, Any]]:
    session = get_session(session_id)
    if session is None:
        return []

    is_jobs_for_resume = session.get("resume_id") and not session.get("job_id")

    with get_connection() as conn:
        if is_jobs_for_resume:
            rows = conn.execute(
                """
                SELECT mr.*, d.filename AS job_filename, d.url AS job_url,
                       d.company AS job_company, d.location AS job_location,
                       d.source AS job_source
                FROM match_results mr
                JOIN documents d ON d.id = mr.job_id
                WHERE mr.session_id = ?
                ORDER BY mr.score DESC
                """,
                (session_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "resume_id": row["resume_id"],
                    "job_id": row["job_id"],
                    "job_filename": row["job_filename"],
                    "job_url": row["job_url"],
                    "job_company": row["job_company"],
                    "job_location": row["job_location"],
                    "job_source": row["job_source"],
                    "score": row["score"],
                    "semantic_score": row["semantic_score"],
                    "keyword_score": row["keyword_score"],
                    "breakdown": json.loads(row["breakdown_json"]),
                    "explanation": row["explanation"],
                }
                for row in rows
            ]

        rows = conn.execute(
            """
            SELECT mr.*, d.filename AS resume_filename
            FROM match_results mr
            JOIN documents d ON d.id = mr.resume_id
            WHERE mr.session_id = ?
            ORDER BY mr.score DESC
            """,
            (session_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "resume_id": row["resume_id"],
            "job_id": row["job_id"],
            "resume_filename": row["resume_filename"],
            "score": row["score"],
            "semantic_score": row["semantic_score"],
            "keyword_score": row["keyword_score"],
            "breakdown": json.loads(row["breakdown_json"]),
            "explanation": row["explanation"],
        }
        for row in rows
    ]


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM match_sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    keys = row.keys()
    return {
        "id": row["id"],
        "mode": row["mode"],
        "job_id": row["job_id"],
        "resume_id": row["resume_id"] if "resume_id" in keys else None,
        "created_at": row["created_at"],
    }


def insert_chat_message(session_id: str, role: str, content: str) -> str:
    message_id = str(uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, session_id, role, content, _utc_now()),
        )
    return message_id


def get_chat_messages(session_id: str) -> list[dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def update_document(doc_id: str, raw_text: str, structured: dict[str, Any]) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE documents
            SET raw_text = ?, structured_json = ?
            WHERE id = ?
            """,
            (raw_text, json.dumps(structured), doc_id),
        )
    return cursor.rowcount > 0


def update_match_explanation(result_id: str, explanation: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE match_results SET explanation = ? WHERE id = ?",
            (explanation, result_id),
        )


def list_jobs(limit: int = 100, origin: str | None = "manual") -> list[dict[str, Any]]:
    """List job documents.

    Defaults to manually added jobs so discovered postings - which arrive in
    bulk on every search - do not swamp the user's curated library.
    """
    query = """
        SELECT id, filename, created_at, origin, source, url, company, location
        FROM documents
        WHERE doc_type = 'job'
    """
    params: list[Any] = []
    if origin is not None:
        query += " AND origin = ?"
        params.append(origin)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [
        {
            "id": row["id"],
            "filename": row["filename"],
            "created_at": row["created_at"],
            "origin": row["origin"],
            "source": row["source"],
            "url": row["url"],
            "company": row["company"],
            "location": row["location"],
        }
        for row in rows
    ]


def delete_document(doc_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return cursor.rowcount > 0


def list_sessions(limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ms.*,
                   jd.filename AS job_filename,
                   rd.filename AS resume_filename
            FROM match_sessions ms
            LEFT JOIN documents jd ON jd.id = ms.job_id
            LEFT JOIN documents rd ON rd.id = ms.resume_id
            ORDER BY ms.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "mode": row["mode"],
            "job_id": row["job_id"],
            "resume_id": row["resume_id"] if "resume_id" in row.keys() else None,
            "job_filename": row["job_filename"],
            "resume_filename": row["resume_filename"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
