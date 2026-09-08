"""Learning pillar.

    User profile / role
            ↓
    Derived persona
            ↓
    Static curation rules  +  learning metadata
            ↓
    Relevant / authorised content
            ↓
    Landing page: Required · Continue · Role path · Best practice · Docs · Quick ref
            ↓
    Learning item  →  started / progress / completed
            ↓
    My Learning: progress and topic coverage

Ownership: Learning owns learning content, learning curation AND learning progress.
Other pillars consume `/for-agent/{id}`; they do not implement their own.

Scope line: progress is learning state and is tracked from Day 1. Using progress or
any behaviour to CHANGE recommendations is future work and is not done here.
Proficiency is deliberately not computed — see `PROFICIENCY_NOTE`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from .. import personas as hub_personas
from ..context import store as context_store
from ..identity import derive_persona, load_profile
from ..marketplace.store import store as marketplace_store
from . import progress as progress_store
from .models import (
    Item,
    ItemDetail,
    ItemWithProgress,
    LearningHome,
    LearningPath,
    MyLearning,
    ProgressIn,
    Section,
    TopicCoverage,
)

_DATA_DIR = Path(os.environ.get("CREDITWIZ_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))

router = APIRouter(prefix="/api/learning", tags=["learning"])

PROFICIENCY_NOTE = (
    "For the MVP the hub displays learning progress and topic coverage. Proficiency will remain a "
    "separate capability until the agreed enterprise measure of proficiency is defined."
)


# ---------------------------------------------------------------- data

def _raw() -> dict:
    with open(_DATA_DIR / "learning.json", encoding="utf-8") as fh:
        return json.load(fh)


def _load() -> tuple[list[LearningPath], list[Item]]:
    raw = _raw()
    return [LearningPath.model_validate(p) for p in raw["paths"]], [Item.model_validate(i) for i in raw["items"]]


def _persona_paths() -> dict[str, list[str]]:
    return {k: v for k, v in _raw().get("persona_paths", {}).items() if not k.startswith("_")}


def _derived_persona_id() -> str:
    return derive_persona(load_profile()).id


def _user_id() -> str:
    return load_profile().id


def _with_progress(items: list[Item], persona_id: str | None) -> list[ItemWithProgress]:
    rows = progress_store.all_for(_user_id())
    out = []
    for i in items:
        r = rows.get(i.id, {})
        out.append(
            ItemWithProgress(
                **i.model_dump(),
                status=r.get("status", "not_started"),
                progress=r.get("progress", 0),
                required=bool(persona_id and persona_id in i.required_for),
            )
        )
    return out


# ---------------------------------------------------------------- curation
# Learning-owned, same explainable idea the Marketplace uses for agents:
# rule-based over static metadata. No behavioural signals feed ranking.
#
#   path affinity   +10 / +6 / +3   by position in the persona's path list
#   persona tag     +2 each
#
# On an agent page the agent link must dominate, so persona affinity there is a
# smaller +5 / +3 / +1 re-ordering nudge.

_PATH_AFFINITY = (10.0, 6.0, 3.0)
_AGENT_PATH_AFFINITY = (5.0, 3.0, 1.0)


def _affinity(path: str, persona_id: str | None, scale: tuple[float, ...]) -> float:
    if not persona_id:
        return 0.0
    paths = _persona_paths().get(persona_id, [])
    return scale[paths.index(path)] if path in paths[: len(scale)] else 0.0


def curation_breakdown(item: Item, persona: hub_personas.Persona | None) -> dict[str, float]:
    tags = {t.lower() for t in (persona.interests.tags if persona else [])}
    return {
        "path_affinity": _affinity(item.path, persona.id if persona else None, _PATH_AFFINITY),
        "persona_tag": 2.0 * len(tags & {t.lower() for t in item.tags}),
    }


def curation_score(item: Item, persona: hub_personas.Persona | None) -> float:
    return sum(curation_breakdown(item, persona).values())


def recommend_for_persona(persona: hub_personas.Persona | None, limit: int = 6) -> list[Item]:
    _, items = _load()
    if persona is None:
        return items[:limit]
    scored = [(curation_score(i, persona), i) for i in items]
    return [i for s, i in sorted(scored, key=lambda si: -si[0]) if s > 0][:limit]


def recommend_for_agent(agent_id: str, persona: str | None = None, limit: int = 3) -> list[Item]:
    """Which learning teaches this agent, ordered for who is asking.

    The explicit agent link dominates so the right content always appears; persona
    only re-orders among items that already relate to this agent.
    """
    agent = marketplace_store.agent(agent_id)
    if agent is None:
        return []
    _, items = _load()
    tags = {t.lower() for t in agent.tags}
    pid = hub_personas.persona_id(persona) if persona else None

    def relevance(i: Item) -> float:
        return (10.0 if agent_id in i.related_agents else 0.0) + 2.0 * len(tags & {t.lower() for t in i.tags})

    ranked = sorted(items, key=lambda i: -(relevance(i) + _affinity(i.path, pid, _AGENT_PATH_AFFINITY)))
    return [i for i in ranked if relevance(i) > 0][:limit]


# ---------------------------------------------------------------- landing page

_DOC_TYPES = ("documentation", "guide", "confluence")


@router.get("", response_model=LearningHome)
def home(persona: str | None = None) -> LearningHome:
    """Role-based landing page: relevant learning first, then the rest of the library."""
    paths, items = _load()
    p = hub_personas.get(persona or _derived_persona_id())
    pid = p.id if p else None
    enriched = _with_progress(items, pid)
    by_id = {i.id: i for i in enriched}

    required = [i for i in enriched if i.required and i.status != "completed"]
    continuing = [i for i in enriched if i.status == "in_progress"]
    role = [by_id[i.id] for i in recommend_for_persona(p, limit=8)]
    role = [i for i in role if i.status != "completed" and not i.required][:4]

    sections: list[Section] = []
    if required:
        sections.append(Section(
            id="required", title="Required for your role",
            subtitle=f"Mandatory for {p.label.lower()}s." if p else "Mandatory learning.",
            items=required))
    if continuing:
        sections.append(Section(id="continue", title="Continue learning",
                                subtitle="Pick up where you left off.", items=continuing))
    if role:
        sections.append(Section(
            id="role", title="Recommended for your role",
            subtitle="Curated from your role and learning metadata." + (f" Tuned for {p.label.lower()}s." if p else ""),
            items=role))
    for sid, title, subtitle, pred in (
        ("best-practice", "Best practices", "How our teams get reliable results.",
         lambda i: i.type == "best-practice"),
        ("docs", "Documentation and guides", "Reference material and how-to guides.",
         lambda i: i.type in _DOC_TYPES),
        ("quick-reference", "Quick references", "One-pagers to keep open while you work.",
         lambda i: i.type == "quick-reference"),
    ):
        picked = [i for i in enriched if pred(i)]
        if picked:
            sections.append(Section(id=sid, title=title, subtitle=subtitle, items=picked))

    return LearningHome(
        persona=pid or "", persona_label=p.label if p else "",
        paths=paths, sections=sections, item_count=len(items),
    )


@router.get("/items", response_model=list[ItemWithProgress])
def list_items(path: str | None = None, type: str | None = None, topic: str | None = None,
               agent: str | None = None, status: str | None = None) -> list[ItemWithProgress]:
    _, items = _load()
    if path:
        items = [i for i in items if i.path == path]
    if type:
        items = [i for i in items if i.type == type]
    if topic:
        items = [i for i in items if topic.lower() in [t.lower() for t in i.topics]]
    if agent:
        items = [i for i in items if agent in i.related_agents]
    out = _with_progress(items, _derived_persona_id())
    if status:
        out = [i for i in out if i.status == status]
    return out


@router.get("/items/{item_id}", response_model=ItemDetail)
def item(item_id: str) -> ItemDetail:
    paths, items = _load()
    current = next((i for i in items if i.id == item_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="Learning item not found")
    pid = _derived_persona_id()
    path_title = next((p.title for p in paths if p.id == current.path), current.path)
    topics = {t.lower() for t in current.topics}
    related = sorted(
        (i for i in items if i.id != current.id),
        key=lambda i: -(3 * len(set(i.related_agents) & set(current.related_agents))
                        + 2 * len(topics & {t.lower() for t in i.topics})
                        + (1 if i.path == current.path else 0)),
    )[:3]
    enriched = {i.id: i for i in _with_progress([current, *related], pid)}
    names = {a.id: a.name for a in marketplace_store.agents if a.id in current.related_agents}
    return ItemDetail(
        **enriched[current.id].model_dump(),
        path_title=path_title,
        related_items=[enriched[r.id] for r in related],
        related_agent_names=names,
    )


# ---------------------------------------------------------------- progress

@router.post("/progress", response_model=ItemWithProgress)
def set_progress(body: ProgressIn) -> ItemWithProgress:
    """Record learning state. Also emits a hub footprint so other pillars can see it."""
    _, items = _load()
    current = next((i for i in items if i.id == body.item_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="Learning item not found")
    pid = _derived_persona_id()
    row = progress_store.record(_user_id(), body.item_id, body.status, body.progress)
    if row["status"] == "completed":
        context_store.record_event({
            "pillar": "learning", "type": "learning_complete",
            "subject_id": current.id, "subject_type": current.type,
            "persona": pid, "topics": current.topics + current.tags,
            "meta": {"path": current.path},
        })
    return ItemWithProgress(**current.model_dump(), status=row["status"], progress=row["progress"],
                            required=pid in current.required_for)


@router.get("/my-learning", response_model=MyLearning)
def my_learning() -> MyLearning:
    """Progress and topic coverage. Factual counts only — no proficiency score."""
    _, items = _load()
    p = hub_personas.get(_derived_persona_id())
    pid = p.id if p else None
    enriched = _with_progress(items, pid)

    # what is relevant to this person: their persona's items plus anything they touched
    mine = [i for i in enriched if (pid and pid in i.personas) or i.status != "not_started"]

    coverage: dict[str, list[int]] = {}
    for i in mine:
        for t in i.topics:
            done, total = coverage.setdefault(t, [0, 0])
            coverage[t] = [done + (1 if i.status == "completed" else 0), total + 1]

    return MyLearning(
        persona=pid or "", persona_label=p.label if p else "",
        completed=sum(1 for i in mine if i.status == "completed"),
        in_progress=sum(1 for i in mine if i.status == "in_progress"),
        not_started=sum(1 for i in mine if i.status == "not_started"),
        required_total=sum(1 for i in mine if i.required),
        required_completed=sum(1 for i in mine if i.required and i.status == "completed"),
        items=sorted(mine, key=lambda i: ({"in_progress": 0, "not_started": 1, "completed": 2}[i.status], i.title)),
        coverage=[TopicCoverage(topic=t, completed=c[0], total=c[1])
                  for t, c in sorted(coverage.items(), key=lambda kv: (-kv[1][1], kv[0]))],
        proficiency_note=PROFICIENCY_NOTE,
    )


# ---------------------------------------------------------------- consumed by other pillars

@router.get("/for-agent/{agent_id}", response_model=list[ItemWithProgress])
def for_agent(agent_id: str, persona: str | None = None) -> list[ItemWithProgress]:
    """Learning that teaches a given agent. Consumed by the Marketplace agent page."""
    pid = persona or _derived_persona_id()
    return _with_progress(recommend_for_agent(agent_id, pid), hub_personas.persona_id(pid))


@router.get("/recommended", response_model=list[ItemWithProgress])
def recommended(persona: str | None = None) -> list[ItemWithProgress]:
    pid = persona or _derived_persona_id()
    return _with_progress(recommend_for_persona(hub_personas.get(pid)), hub_personas.persona_id(pid))


@router.get("/curation")
def curation(persona: str | None = None) -> dict:
    """Why the learning rows are ordered the way they are. Rule-based and explainable."""
    p = hub_personas.get(persona or _derived_persona_id())
    _, items = _load()
    rows = []
    for i in items:
        parts = curation_breakdown(i, p)
        rows.append({"item_id": i.id, "title": i.title, "type": i.type, "path": i.path,
                     "total": round(sum(parts.values()), 2),
                     "components": {k: round(x, 2) for k, x in parts.items()}})
    rows.sort(key=lambda r: -r["total"])
    return {
        "persona": p.id if p else None,
        "persona_label": p.label if p else None,
        "persona_paths": _persona_paths().get(p.id, []) if p else [],
        "inputs": ["derived persona", "learning metadata"],
        "excluded": ["behavioural footprints and progress (tracked, not used for ranking in the MVP)"],
        "proficiency": PROFICIENCY_NOTE,
        "ranked": rows,
    }
