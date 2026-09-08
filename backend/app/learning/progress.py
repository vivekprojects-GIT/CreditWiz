"""Learning progress — state owned by the Learning pillar, stored in SQLite.

Why SQLite and not a JSON file: progress is *mutable per-user state* with
read-modify-write on every update. A JSON file has to be rewritten whole and
races as soon as there is more than one worker. SQLite gives an atomic upsert,
needs no server, and ships as a single file.

The split is deliberate and is the production shape:

    state   → SQLite      (this file: who is where in what)
    events  → JSONL       (app/context: append-only footprints, stream-shaped)
    content → JSON files  (data/: authored, version-controlled, handed over)

This is NOT the shared footprint store. Footprints are hub-wide observations
("this happened"); progress is Learning's record of where a user is. Learning
also emits a footprint on completion so the hub sees it.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_VAR_DIR = Path(os.environ.get("CREDITWIZ_VAR_DIR", Path(__file__).resolve().parents[2] / "var"))
_DB_NAME = "learning.db"
_lock = threading.Lock()

Status = Literal["not_started", "in_progress", "completed"]
_ORDER = {"not_started": 0, "in_progress": 1, "completed": 2}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_progress (
    user_id      TEXT NOT NULL,
    item_id      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'not_started',
    progress     INTEGER NOT NULL DEFAULT 0,
    started_at   TEXT,
    completed_at TEXT,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (user_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_progress_user ON learning_progress (user_id, status);
"""


def _db_path() -> Path:
    return _VAR_DIR / _DB_NAME


def _connect() -> sqlite3.Connection:
    _VAR_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path(), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def all_for(user_id: str) -> dict[str, dict]:
    """item_id -> progress row for one user."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT item_id, status, progress, started_at, completed_at, updated_at "
            "FROM learning_progress WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return {r["item_id"]: dict(r) for r in rows}


def record(user_id: str, item_id: str, status: Status, progress: int | None = None) -> dict:
    """Upsert one row. Status never regresses and progress never goes backwards."""
    now = _now()
    pct = 100 if status == "completed" else max(0, min(100, progress if progress is not None else 0))

    with _lock, _connect() as conn:
        existing = conn.execute(
            "SELECT status, progress, started_at FROM learning_progress WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        ).fetchone()

        if existing is None:
            new_status, new_pct, started = status, pct, now
        else:
            new_status = status if _ORDER[status] >= _ORDER[existing["status"]] else existing["status"]
            new_pct = max(existing["progress"], pct)
            started = existing["started_at"] or now
        if new_status == "completed":
            new_pct = 100

        conn.execute(
            """
            INSERT INTO learning_progress (user_id, item_id, status, progress, started_at, completed_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET
                status       = excluded.status,
                progress     = excluded.progress,
                completed_at = COALESCE(learning_progress.completed_at, excluded.completed_at),
                updated_at   = excluded.updated_at
            """,
            (user_id, item_id, new_status, new_pct, started,
             now if new_status == "completed" else None, now),
        )
        row = conn.execute(
            "SELECT item_id, status, progress, started_at, completed_at, updated_at "
            "FROM learning_progress WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        ).fetchone()
    return dict(row)
