import sqlite3

from app import db
from app.config import settings


def test_migrate_legacy_not_null_job_id(tmp_path, monkeypatch):
  """Old DBs created job_id as NOT NULL; seeker sessions need it nullable."""
  db_path = tmp_path / "legacy.db"
  monkeypatch.setattr(settings, "database_path", db_path)
  monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")

  conn = sqlite3.connect(db_path)
  conn.executescript(
      """
      CREATE TABLE documents (
          id TEXT PRIMARY KEY,
          doc_type TEXT NOT NULL,
          filename TEXT NOT NULL,
          raw_text TEXT NOT NULL,
          structured_json TEXT NOT NULL,
          created_at TEXT NOT NULL
      );
      CREATE TABLE match_sessions (
          id TEXT PRIMARY KEY,
          mode TEXT NOT NULL,
          job_id TEXT NOT NULL,
          created_at TEXT NOT NULL
      );
      """
  )
  conn.close()

  db.init_db()

  with db.get_connection() as conn:
    cols = {row[1]: row[3] for row in conn.execute("PRAGMA table_info(match_sessions)").fetchall()}
  assert cols["job_id"] == 0
  assert cols["resume_id"] == 0

  session_id = db.create_match_session(resume_id="resume-1")
  assert session_id
