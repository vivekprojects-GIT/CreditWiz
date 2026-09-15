"""Non-sensitive session telemetry: what the assistant did, never what was asked.

One hub_sessions row per answered question: ids, intents, pillars, what was
recommended, what the person opened, their feedback and how long it took. No
question text, no client, no deal. Those live in the browser session alone.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from .. import database
from ..auth import user_id


def save(
    *,
    turn_id: str,
    session_id: str,
    intents: list[str],
    activity: str | None,
    pillars: list[str],
    recommended: list[str],
    sensitivity: str,
    plan_source: str,
    reply_source: str,
    latency_ms: int,
) -> None:
    with database.connect(write=True) as conn:
        conn.execute(
            "INSERT INTO hub_sessions(id,session_id,user_id,intents,activity,selected_pillars,"
            "recommended_asset_ids,sensitivity,plan_source,reply_source,latency_ms,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                turn_id,
                session_id,
                user_id(),
                json.dumps(intents),
                activity,
                json.dumps(pillars),
                json.dumps(recommended),
                sensitivity,
                plan_source,
                reply_source,
                latency_ms,
                datetime.now(UTC).isoformat(timespec="milliseconds"),
            ),
        )


def feedback(turn_id: str, helpful: bool) -> bool:
    with database.connect(write=True) as conn:
        cur = conn.execute(
            "UPDATE hub_sessions SET feedback=? WHERE id=? AND user_id=?",
            ("helpful" if helpful else "not_helpful", turn_id, user_id()),
        )
        return cur.rowcount == 1


def selected(turn_id: str, ref: str) -> bool:
    """Record that they opened something the turn recommended. Only refs the
    turn actually showed are kept, so the column holds ids and nothing else."""
    with database.connect(write=True) as conn:
        row = conn.execute(
            "SELECT recommended_asset_ids, selected_asset_ids FROM hub_sessions WHERE id=? AND user_id=?",
            (turn_id, user_id()),
        ).fetchone()
        if row is None or ref not in json.loads(row["recommended_asset_ids"]):
            return False
        chosen = json.loads(row["selected_asset_ids"])
        if ref not in chosen:
            chosen.append(ref)
            conn.execute(
                "UPDATE hub_sessions SET selected_asset_ids=? WHERE id=?", (json.dumps(chosen), turn_id)
            )
        return True
