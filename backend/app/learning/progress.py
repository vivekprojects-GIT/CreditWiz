"""Monotonic per-user learning state and exactly-once completion events in SQL."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from .. import database

Status = Literal["not_started", "in_progress", "completed"]
_ORDER = {"not_started": 0, "in_progress": 1, "completed": 2}


def all_for(user_id: str) -> dict[str, dict]:
    with database.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM learning_progress WHERE user_id=?", (user_id,)
        ).fetchall()
    return {r["item_id"]: dict(r) for r in rows}


def record(
    user_id: str,
    item_id: str,
    status: Status,
    progress: int | None = None,
    completion_event: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    pct = 100 if status == "completed" else min(99, max(0, progress or 0))
    # BEGIN IMMEDIATE serializes read/modify/write across threads AND processes.
    with database.connect(write=True) as conn:
        existing = conn.execute(
            "SELECT * FROM learning_progress WHERE user_id=? AND item_id=?",
            (user_id, item_id),
        ).fetchone()
        previous = existing["status"] if existing else "not_started"
        next_status = max((previous, status), key=_ORDER.__getitem__)
        next_pct = (
            100
            if next_status == "completed"
            else max(existing["progress"] if existing else 0, pct)
        )
        started = (existing["started_at"] if existing else None) or (
            now if next_status != "not_started" else None
        )
        completed = (existing["completed_at"] if existing else None) or (
            now if next_status == "completed" else None
        )
        conn.execute(
            "INSERT INTO learning_progress VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(user_id,item_id) DO UPDATE SET status=excluded.status,progress=excluded.progress,"
            "started_at=excluded.started_at,completed_at=excluded.completed_at,updated_at=excluded.updated_at",
            (user_id, item_id, next_status, next_pct, started, completed, now),
        )
        if next_status == "completed" and previous != "completed" and completion_event:
            from ..context.store import record_event

            record_event(
                completion_event,
                conn=conn,
                uid=user_id,
                event_key=f"completion:{user_id}:{item_id}",
            )
        row = conn.execute(
            "SELECT * FROM learning_progress WHERE user_id=? AND item_id=?",
            (user_id, item_id),
        ).fetchone()
    return dict(row)
