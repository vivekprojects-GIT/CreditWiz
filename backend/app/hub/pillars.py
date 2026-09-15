"""The pillar nodes. Each asks its pillar's agent, inside what the governance
gate allows. They run in parallel; one failing costs its own group, not the
answer.

    prompts      the Prompts & Skills agent (prompts/agent.py)
    marketplace  Discover's own retrieval, untouched, then the agents' rerank
    learning     the Learning agent (learning/agent.py)
    community    word matching over experts and communities: no agent yet

Every agent runs one pipeline (retrieval/agent.py): hybrid retrieval, a
relevance gate, then a rerank by the model where the data policy lets it
read the request. Each is asked two queries when the planner rewrote the
request for it, the masked request as typed and the rewrite, fused so a
rewrite can add recall but never lose what the person's own words found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..data import PILLARS
from ..journeys.models import AssetCard, Journey
from ..learning import agent as learning_agent
from ..prompts import agent as prompts_agent
from ..prompts import draft as drafting
from ..retrieval.agent import RESULT_LIMIT, judged_order, rerank
from ..retrieval.models import AgentHit
from ..text import subject_stems, word_starts
from .guardrails import Entitlements
from .models import Pillar, PillarGroup, PillarHit

SHOWN = 3

_HEAD: dict[str, tuple[str, str]] = {
    "prompts": ("Prompts", "/library"),
    "marketplace": ("Agents", "/marketplace"),
    "learning": ("Learning", "/learning/catalog"),
    "community": ("Community", "/community"),
}
_AGENTS = "AI agent marketplace: approved agents that each do a task end to end"


@dataclass
class Run:
    """What one pillar's agent returned, and how it found it."""

    hits: list[PillarHit] = field(default_factory=list)
    retrieval: Literal["hybrid", "keyword", "words"] = "words"
    reranked: bool = False


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
        reranked=run.reranked,
    )


# ------------------------------------------------------------------ prompts


def prompts(queries: list[str], ents: Entitlements, toolkit: list[AssetCard], rerank_query: str | None) -> Run:
    found, hits = prompts_agent.find(
        queries, ents.prompts, desk=ents.desk, exclude=_taken(toolkit), rerank_query=rerank_query
    )
    return Run(_shown(hits), found.retrieval, found.reranked)


def draft_for(goal: str, ents: Entitlements, job_title: str, department: str):
    return drafting.compose(goal, job_title=job_title, department=department, pool=ents.prompts)


# -------------------------------------------------------------- marketplace


def marketplace(
    queries: list[str],
    ents: Entitlements,
    persona_id: str,
    journey: Journey | None,
    toolkit: list[AssetCard],
    rerank_query: str | None,
) -> Run:
    """Hybrid retrieval as Discover runs it (semantic and BM25, fused by
    rank, gated for relevance), for each query, then fused once more with
    task relevance (the job's own agents) and persona relevance. The last two
    only reorder what retrieval found relevant; they never add an agent. The
    shortlist is then reranked like every other agent's."""
    from ..marketplace import keyword, search, semantic
    from ..marketplace.store import store as agent_store

    if keyword.index.size == 0:
        keyword.index.sync(agent_store.all_agents)
    allowed = {a.id for a in ents.agents}
    persona = agent_store.persona(persona_id)
    semantic_up = semantic.index.available
    rankings: list[dict[str, float]] = []
    found = {}
    for q in queries:
        similar = semantic.index.search(search.retrieval_text(q), groups=ents.groups) if semantic_up else None
        keywords = keyword.index.search(search.keyword_text(q), allowed=allowed)
        matches = search.rank(
            q, search.local_intent(q), ents.agents, persona=persona, similar=similar, keywords=keywords
        )
        rankings.append({m.agent.id: m.score for m in matches})
        for m in matches:
            found.setdefault(m.agent.id, m)
    retrieval = "hybrid" if semantic_up else "keyword"
    if not found:
        return Run([], retrieval)

    job_agents = [r.ref.split(":", 1)[1] for r in (journey.assets if journey else []) if r.ref.startswith("agent:")]
    task_rank = {aid: float(len(job_agents) - i) for i, aid in enumerate(job_agents) if aid in found}
    persona_rank = {aid: 1.0 for aid, m in found.items() if persona_id in m.agent.personas}
    fused = search.rrf(*rankings, task_rank, persona_rank)
    taken = _taken(toolkit)
    ordered = [aid for aid in sorted(fused, key=lambda i: -fused[i]) if f"agent:{aid}" not in taken][:RESULT_LIMIT]
    fits: dict[str, str | None] = {}
    reranked = False
    if rerank_query:
        judged = rerank(
            _AGENTS,
            rerank_query,
            [
                (aid, f"{found[aid].agent.name}. {found[aid].agent.tagline} "
                 f"Capabilities: {', '.join(found[aid].agent.capabilities)}.")
                for aid in ordered
            ],
        )
        if judged is not None:
            placed = judged_order(ordered, judged)
            ordered, fits, reranked = [aid for aid, _ in placed], dict(placed), True
    hits = [
        PillarHit(
            ref=f"agent:{aid}",
            kind="agent",
            title=found[aid].agent.name,
            summary=found[aid].agent.tagline,
            href=f"/marketplace/agents/{aid}",
            why=found[aid].why,
            meta=found[aid].agent.status.replace("_", " ").capitalize(),
            fit=fits.get(aid),
        )
        for aid in ordered[:SHOWN]
    ]
    return Run(hits, retrieval, reranked)


# ----------------------------------------------------------------- learning


def learning(
    queries: list[str], ents: Entitlements, persona_id: str, toolkit: list[AssetCard], rerank_query: str | None
) -> Run:
    found, hits = learning_agent.find(
        queries, ents.learning, persona_id=persona_id, exclude=_taken(toolkit), rerank_query=rerank_query
    )
    return Run(_shown(hits), found.retrieval, found.reranked)


# ---------------------------------------------------------------- community


def community(queries: list[str], ents: Entitlements, journey: Journey | None, toolkit: list[AssetCard]) -> Run:
    """Experts and communities from the catalogue, and Community's own pages.
    The job's own people rank first at equal fit."""
    people = [a for a in ents.assets if a.kind in ("expert", "community")]
    job_refs = {r.ref for r in (journey.assets if journey else []) if r.intent == "ask"}
    pages = next((p.sections for p in PILLARS if p.id == "community"), [])
    starts_by_query = [word_starts(subject_stems(q)) for q in queries]

    def fit(text: str) -> int:
        low = text.lower()
        return max((sum(bool(s.search(low)) for s in starts) for starts in starts_by_query), default=0)

    scored: list[tuple[int, PillarHit]] = []
    for a in people:
        score = fit(" ".join([a.title, a.summary, a.trust.purpose]))
        if score:
            scored.append(
                (
                    score + (f"asset:{a.id}" in job_refs),
                    PillarHit(
                        ref=f"asset:{a.id}",
                        kind=a.kind,
                        title=a.title,
                        summary=a.summary,
                        href=a.action_url,
                        meta=a.provided_by,
                    ),
                )
            )
    for s in pages:
        score = fit(f"{s.title} {s.blurb}")
        if score:
            scored.append(
                (score, PillarHit(ref=f"page:{s.href}", kind="page", title=s.title, summary=s.blurb, href=s.href, meta="Community"))
            )
    taken = _taken(toolkit)
    scored.sort(key=lambda sh: -sh[0])
    return Run([h for _, h in scored if h.ref not in taken][:SHOWN])
