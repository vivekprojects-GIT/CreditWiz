"""Persistent preferences and local access-request workflow for the MVP."""

import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .auth import user_id
from .database import connect
from .marketplace.store import store

router = APIRouter(prefix="/api", tags=["account"])


class Preferences(BaseModel):
    default_domain: str = "all"
    # The MVP has no email delivery service; do not offer nonfunctional toggles.
    show_learning_reminders: bool = True


@router.get("/preferences", response_model=Preferences)
def preferences():
    with connect() as conn:
        row = conn.execute(
            "SELECT value FROM preferences WHERE user_id=?", (user_id(),)
        ).fetchone()
    return Preferences.model_validate(json.loads(row[0])) if row else Preferences()


@router.put("/preferences", response_model=Preferences)
def save_preferences(body: Preferences):
    if body.default_domain != "all" and body.default_domain not in store.domains():
        raise HTTPException(422, "Unknown business domain")
    with connect(write=True) as conn:
        conn.execute(
            "INSERT INTO preferences VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET value=excluded.value",
            (user_id(), body.model_dump_json()),
        )
    return body


class AccessRequest(BaseModel):
    agent_id: str
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/access-requests")
def request_access(body: AccessRequest):
    if len(body.reason.strip()) < 10:
        raise HTTPException(422, "Provide a business reason of at least 10 characters")
    agent = store.agent(body.agent_id)
    if agent is None:
        raise HTTPException(404, "Agent not found")
    with connect(write=True) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO access_requests(id,user_id,agent_id,reason,created_at) VALUES (?,?,?,?,?)",
            (
                uuid.uuid4().hex,
                user_id(),
                agent.id,
                body.reason.strip(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM access_requests WHERE user_id=? AND agent_id=?",
            (user_id(), agent.id),
        ).fetchone()
    return dict(row)


@router.get("/access-requests")
def access_requests():
    allowed = {a.id: a.name for a in store.agents}
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM access_requests WHERE user_id=? ORDER BY created_at DESC",
            (user_id(),),
        ).fetchall()
    return [
        {**dict(r), "agent_name": allowed[r["agent_id"]]}
        for r in rows
        if r["agent_id"] in allowed
    ]
