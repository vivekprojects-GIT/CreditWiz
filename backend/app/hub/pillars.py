"""The pillar nodes. Each asks its pillar's agent, inside what the governance
gate allows. They run in parallel; one failing costs its own group, not the
answer.

    marketplace  Discover's own retrieval, untouched
    learning     the Learning agent (learning/agent.py)

Every agent runs one pipeline (retrieval/agent.py): hybrid retrieval and a
relevance gate. No model reads a shortlist. Each is asked two queries when the planner rewrote the
request for it, the masked request as typed and the rewrite; a record keeps its
best showing, so a rewrite can add recall but never lose what the person's own
words found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..journeys.models import AssetCard, Journey
from ..learning import agent as learning_agent
from ..retrieval.agent import RESULT_LIMIT
from ..retrieval.models import AgentHit
from .guardrails import Entitlements
from .models import Pillar, PillarGroup, PillarHit

SHOWN = 3

_HEAD: dict[str, tuple[str, str]] = {
    "marketplace": ("Agents", "/marketplace"),
    "learning": ("Learning", "/learning/catalog"),
}


@dataclass
class Run:
    """What one pillar's agent returned, and how it found it."""

    hits: list[PillarHit] = field(default_factory=list)
    retrieval: Literal["hybrid", "keyword", "words"] = "words"


def _queries(retrieval: str, subquery: str) -> list[str]:
    return [q for q in dict.fromkeys([retrieval, subquery]) if q.strip()]


def _taken(toolkit: list[AssetCard]) -> set[str]:
    """Already on the job's own toolkit, so not repeated under a pillar."""
    return {c.ref for c in toolkit}


def _shown(hits: list[AgentHit]) -> list[PillarHit]:
    fields = set(PillarHit.model_fields)
    return [PillarHit(**h.model_dump(include=fields)) for h in hits[:SHOWN]]


def group(pillar: Pillar, query: str, run: Run, ms: int) -> PillarGroup:
    label, href = _HEAD[pillar]
    return PillarGroup(
        pillar=pillar,
        label=label,
        href=href,
        query=query,
        hits=run.hits,
        ms=ms,
        retrieval=run.retrieval,
    )


# -------------------------------------------------------------- marketplace


def _closeness(m) -> tuple[float, float]:
    return (m.similarity or 0.0, m.keyword or 0.0)


def marketplace(
    queries: list[str],
    ents: Entitlements,
    persona_id: str,
    journey: Journey | None,
    toolkit: list[AssetCard],
) -> Run:
    """Hybrid retrieval as Discover runs it (semantic and BM25, gated for
    relevance, closest in meaning first), for each query. An agent keeps its
    best showing across the queries; one built for the person's role leads
    only at equal similarity."""
    from ..marketplace import keyword, search, semantic
    from ..marketplace.store import store as agent_store

    if keyword.index.size == 0:
        keyword.index.sync(agent_store.all_agents)
    allowed = {a.id for a in ents.agents}
    persona = agent_store.persona(persona_id)
    semantic_up = semantic.index.available
    found = {}
    for q in queries:
        similar = semantic.index.search(search.retrieval_text(q), groups=ents.groups) if semantic_up else None
        keywords = keyword.index.search(search.keyword_text(q), allowed=allowed)
        matches = search.rank(
            q, search.local_intent(q), ents.agents, persona=persona, similar=similar, keywords=keywords
        )
        for m in matches:
            best = found.get(m.agent.id)
            if best is None or _closeness(m) > _closeness(best):
                found[m.agent.id] = m
    retrieval = "hybrid" if semantic_up else "keyword"
    if not found:
        return Run([], retrieval)

    def closest_first(aid: str) -> tuple:
        m = found[aid]
        return (-(m.similarity or 0.0), persona_id not in m.agent.personas, -(m.keyword or 0.0), aid)

    taken = _taken(toolkit)
    ordered = [aid for aid in sorted(found, key=closest_first) if f"agent:{aid}" not in taken][:RESULT_LIMIT]
    hits = [
        PillarHit(
            ref=f"agent:{aid}",
            kind="agent",
            title=found[aid].agent.name,
            summary=found[aid].agent.tagline,
            href=f"/marketplace/agents/{aid}",
            why=found[aid].why,
            meta=found[aid].agent.status.replace("_", " ").capitalize(),
        )
        for aid in ordered[:SHOWN]
    ]
    return Run(hits, retrieval)


# ----------------------------------------------------------------- learning


def learning(
    queries: list[str], ents: Entitlements, persona_id: str, toolkit: list[AssetCard]
) -> Run:
    found, hits = learning_agent.find(queries, ents.learning, persona_id=persona_id, exclude=_taken(toolkit))
    return Run(_shown(hits), found.retrieval)
