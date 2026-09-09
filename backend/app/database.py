"""SQLite persistence for the hub. Connections always close; writes are transactions."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

VAR_DIR = Path(
    os.environ.get("CREDITWIZ_VAR_DIR", Path(__file__).resolve().parents[1] / "var")
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL DEFAULT '',
 profile TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS login_attempts (address TEXT PRIMARY KEY, failures INTEGER NOT NULL, until_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS preferences (user_id TEXT PRIMARY KEY REFERENCES users(id), value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notification_reads (
 user_id TEXT NOT NULL REFERENCES users(id), notification_id TEXT NOT NULL,
 PRIMARY KEY(user_id, notification_id)
);
CREATE TABLE IF NOT EXISTS learning_progress (
 user_id TEXT NOT NULL, item_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'not_started',
 progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
 started_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL,
 PRIMARY KEY(user_id, item_id)
);
CREATE TABLE IF NOT EXISTS learning_ratings (
 user_id TEXT NOT NULL REFERENCES users(id), item_id TEXT NOT NULL,
 stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(user_id, item_id)
);
CREATE INDEX IF NOT EXISTS learning_ratings_item ON learning_ratings(item_id);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL, at TEXT NOT NULL, payload TEXT NOT NULL,
 event_key TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS events_user ON events(user_id, at);
CREATE TABLE IF NOT EXISTS feedback (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL, at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS feedback_user ON feedback(user_id, at);
CREATE TABLE IF NOT EXISTS access_requests (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), agent_id TEXT NOT NULL,
 reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
 UNIQUE(user_id, agent_id)
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Import legacy state once, without changing or deleting the original files."""
    if conn.execute("SELECT 1 FROM migrations WHERE name='legacy-v1'").fetchone():
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        if not conn.execute(
            "SELECT 1 FROM migrations WHERE name='legacy-v1'"
        ).fetchone():
            old = VAR_DIR / "learning.db"
            if old.exists():
                legacy = sqlite3.connect(f"{old.as_uri()}?mode=ro", uri=True)
                try:
                    for row in legacy.execute(
                        "SELECT user_id,item_id,status,progress,started_at,completed_at,updated_at FROM learning_progress"
                    ):
                        conn.execute(
                            "INSERT OR IGNORE INTO learning_progress VALUES (?,?,?,?,?,?,?)",
                            tuple(row),
                        )
                finally:
                    legacy.close()
            # Older builds used a JSON progress array. SQL rows take precedence.
            old_json = VAR_DIR / "learning_progress.json"
            if old_json.exists():
                rows = json.loads(old_json.read_text(encoding="utf-8"))
                for row in rows:
                    conn.execute(
                        "INSERT OR IGNORE INTO learning_progress VALUES (?,?,?,?,?,?,?)",
                        (
                            row["user_id"],
                            row["item_id"],
                            row["status"],
                            row.get("progress", 0),
                            row.get("started_at"),
                            row.get("completed_at"),
                            row.get(
                                "updated_at", datetime.now(UTC).isoformat()
                            ),
                        ),
                    )
            # The legacy prototype had exactly one profile; retain that provenance.
            profile_file = (
                Path(
                    os.environ.get(
                        "CREDITWIZ_DATA_DIR",
                        Path(__file__).resolve().parents[1] / "data",
                    )
                )
                / "user.json"
            )
            legacy_user = json.loads(profile_file.read_text(encoding="utf-8"))["id"]
            for name, table in (
                ("interactions.jsonl", "events"),
                ("feedback.jsonl", "feedback"),
            ):
                path = VAR_DIR / name
                if not path.exists():
                    continue
                for index, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines()
                ):
                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict):
                            continue
                        if not isinstance(record.get("meta"), dict):
                            record["meta"] = {}
                        record["meta"]["legacy_import"] = True
                        conn.execute(
                            f"INSERT OR IGNORE INTO {table} (id,user_id,at,payload) VALUES (?,?,?,?)",
                            (
                                f"legacy-{table}-{index}",
                                legacy_user,
                                record.get("at", ""),
                                json.dumps(record),
                            ),
                        )
                    except (ValueError, TypeError):
                        continue
            conn.execute("INSERT INTO migrations VALUES ('legacy-v1')")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


# Creating the schema and checking the migration on every single connection cost
# more than the queries themselves: one /api/learning request opened 69
# connections. Do it once per database file. Keyed by path, not a bare flag, so
# tests that point VAR_DIR at a fresh tmp_path still get their schema built.
_ready: set[str] = set()
_ready_lock = threading.Lock()


def _ensure_ready(conn: sqlite3.Connection, path: str) -> None:
    if path in _ready:
        return
    with _ready_lock:
        if path in _ready:
            return
        conn.executescript(SCHEMA)
        _migrate(conn)
        _ready.add(path)


@contextmanager
def connect(*, write: bool = False):
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    database = str((VAR_DIR / "hub.db").resolve())
    conn = sqlite3.connect(database, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_ready(conn, database)
        if write:
            conn.execute("BEGIN IMMEDIATE")
        yield conn
        if write:
            conn.commit()
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()
