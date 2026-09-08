"""Append-only footprint store for the whole hub.

MVP: JSON Lines under backend/var (interactions.jsonl, feedback.jsonl). Every
pillar writes here through the same API. Swap `_append` / `_read` for a real
store (DynamoDB, Postgres, an event bus) without touching any pillar.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

_VAR_DIR = Path(os.environ.get("CREDITWIZ_VAR_DIR", Path(__file__).resolve().parents[2] / "var"))
_EVENTS = "interactions.jsonl"
_FEEDBACK = "feedback.jsonl"
_lock = threading.Lock()

# Topic weight by how much intent the interaction shows.
_WEIGHTS: dict[str, float] = {
    "search": 1.0,
    "view": 0.6,
    "agent_view": 0.6,
    "learning_view": 0.8,
    "click": 0.8,
    "agent_click": 0.8,
    "launch": 2.0,
    "agent_launch": 2.0,
    "request_access": 1.6,
    "documentation_click": 1.0,
    "architecture_click": 1.0,
    "collaborate": 1.2,
    "learning_complete": 1.8,
    "feedback_positive": 0.5,
    "feedback_negative": 0.2,
}


def _append(name: str, record: dict) -> str:
    record_id = uuid.uuid4().hex[:12]
    line = {"id": record_id, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    _VAR_DIR.mkdir(parents=True, exist_ok=True)
    with _lock, open(_VAR_DIR / name, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return record_id


def _read(name: str) -> list[dict]:
    path = _VAR_DIR / name
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def record_event(record: dict) -> str:
    return _append(_EVENTS, record)


def record_feedback(record: dict) -> str:
    return _append(_FEEDBACK, record)


def events() -> list[dict]:
    return _read(_EVENTS)


def feedback() -> list[dict]:
    return _read(_FEEDBACK)


def derive_interests(limit: int = 8) -> list[dict]:
    """Aggregate topics across every pillar into weighted interest signals.

    Demonstrates the shared-context seam. Nothing in the MVP ranks on this:
    Swim Lane 1 curation uses the derived persona only.
    """
    weights: dict[str, float] = defaultdict(float)
    counts: Counter[str] = Counter()
    pillars: dict[str, set[str]] = defaultdict(set)

    for ev in events():
        w = _WEIGHTS.get(ev.get("type", ""), 0.5)
        pillar = ev.get("pillar", "hub")
        for topic in ev.get("topics") or []:
            key = str(topic).strip().lower()
            if not key:
                continue
            weights[key] += w
            counts[key] += 1
            pillars[key].add(pillar)

    if not weights:
        return []
    top = max(weights.values())
    ranked = sorted(weights.items(), key=lambda kv: -kv[1])[:limit]
    return [
        {"topic": t, "weight": round(w / top, 2), "events": counts[t], "pillars": sorted(pillars[t])}
        for t, w in ranked
    ]


def summary() -> dict:
    evs = events()
    fbs = feedback()
    by_pillar: dict[str, Counter[str]] = defaultdict(Counter)
    for ev in evs:
        by_pillar[ev.get("pillar", "hub")][ev.get("type", "unknown")] += 1
    helpful = sum(1 for f in fbs if f.get("helpful"))
    return {
        "total_events": len(evs),
        "total_feedback": len(fbs),
        "helpful": helpful,
        "not_helpful": len(fbs) - helpful,
        "by_pillar": [
            {"pillar": p, "events": sum(c.values()), "types": dict(c)}
            for p, c in sorted(by_pillar.items(), key=lambda kv: -sum(kv[1].values()))
        ],
        "recent_missing": [f["missing"] for f in fbs if f.get("missing")][-10:],
    }
