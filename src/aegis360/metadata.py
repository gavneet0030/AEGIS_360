"""SQLite metadata for local ingestion history; uploaded row data is never stored here."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("""CREATE TABLE IF NOT EXISTS ingestion_runs (
        job_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('succeeded', 'failed')),
        sha256 TEXT,
        rows INTEGER NOT NULL DEFAULT 0,
        columns INTEGER NOT NULL DEFAULT 0,
        duration_ms INTEGER NOT NULL DEFAULT 0,
        error_type TEXT
    )""")
    connection.commit()
    return connection


def record_run(
    path: Path,
    *,
    status: str,
    sha256: str | None = None,
    rows: int = 0,
    columns: int = 0,
    duration_ms: int = 0,
    error_type: str | None = None,
) -> str:
    if status not in {"succeeded", "failed"}:
        raise ValueError("Invalid ingestion status.")
    job_id = str(uuid.uuid4())
    with _connect(path) as connection:
        connection.execute(
            "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                datetime.now(timezone.utc).isoformat(),
                status,
                sha256,
                int(rows),
                int(columns),
                int(duration_ms),
                error_type,
            ),
        )
    return job_id


def recent_runs(path: Path, limit: int = 50):
    if not 1 <= limit <= 200:
        raise ValueError("History limit must be between 1 and 200.")
    if not path.exists():
        return []
    with _connect(path) as connection:
        return connection.execute(
            "SELECT job_id, created_at, status, sha256, rows, columns, duration_ms, error_type "
            "FROM ingestion_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
