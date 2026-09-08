"""User-scoped SQL footprints. No behavioral signal is used for MVP ranking."""

from __future__ import annotations
import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from .. import database
from ..auth import user_id

_WEIGHTS = {
    "search": 1.0,
    "view": 0.6,
    "learning_view": 0.8,
    "click": 0.8,
    "launch": 2.0,
    "request_access": 1.6,
    "documentation_click": 1.0,
    "architecture_click": 1.0,
    "collaborate": 1.2,
    "learning_complete": 1.8,
    # A deliberate act on a specific item, so it outweighs a passing view, but it
    # is one click and should not rival finishing the content.
    "rating": 1.2,
    "feedback_positive": 0.5,
    "feedback_negative": 0.2,
}


def _insert(
    conn, table: str, record: dict, uid: str, event_key: str | None = None
) -> str:
    rid = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    values = (rid, uid, now, json.dumps(record, ensure_ascii=False))
    if table == "events":
        conn.execute(
            "INSERT OR IGNORE INTO events(id,user_id,at,payload,event_key) VALUES (?,?,?,?,?)",
            (*values, event_key),
        )
    else:
        conn.execute(
            "INSERT INTO feedback(id,user_id,at,payload) VALUES (?,?,?,?)", values
        )
    return rid


def record_event(
    record: dict, *, conn=None, uid: str | None = None, event_key: str | None = None
) -> str:
    uid = uid or user_id()
    if conn is not None:
        return _insert(conn, "events", record, uid, event_key)
    with database.connect(write=True) as db:
        return _insert(db, "events", record, uid, event_key)


def record_feedback(record: dict) -> str:
    with database.connect(write=True) as conn:
        return _insert(conn, "feedback", record, user_id())


def _read(table: str) -> list[dict]:
    with database.connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE user_id=? ORDER BY at,id", (user_id(),)
        ).fetchall()
    return [
        {
            **json.loads(r["payload"]),
            "id": r["id"],
            "at": r["at"],
            "user_id": r["user_id"],
        }
        for r in rows
    ]


def events() -> list[dict]:
    return _read("events")


def feedback() -> list[dict]:
    return _read("feedback")


def derive_interests(limit: int = 8) -> list[dict]:
    weights: dict[str, float] = defaultdict(float)
    counts: Counter = Counter()
    pillars: dict[str, set] = defaultdict(set)
    for ev in events():
        for topic in {
            str(t).strip().lower() for t in ev.get("topics", []) if str(t).strip()
        }:
            weights[topic] += _WEIGHTS.get(ev.get("type", ""), 0.5)
            counts[topic] += 1
            pillars[topic].add(ev.get("pillar", "hub"))
    maximum = max(weights.values(), default=1)
    return [
        {
            "topic": t,
            "weight": round(w / maximum, 2),
            "events": counts[t],
            "pillars": sorted(pillars[t]),
        }
        for t, w in sorted(weights.items(), key=lambda x: -x[1])[:limit]
    ]


def summary() -> dict:
    evs, fbs = events(), feedback()
    grouped: dict[str, Counter] = defaultdict(Counter)
    for ev in evs:
        grouped[ev.get("pillar", "hub")][ev["type"]] += 1
    positive = sum(bool(f.get("helpful")) for f in fbs)
    return {
        "total_events": len(evs),
        "total_feedback": len(fbs),
        "helpful": positive,
        "not_helpful": len(fbs) - positive,
        "by_pillar": [
            {"pillar": p, "events": sum(c.values()), "types": dict(c)}
            for p, c in sorted(grouped.items())
        ],
        "recent_missing": [f["missing"] for f in fbs if f.get("missing")][-10:],
    }
