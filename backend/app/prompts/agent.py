"""The Prompts & Skills agent.

Finds validated prompts, and what colleagues contributed through Create, for
a request: the retrieval Discover runs (retrieval/agent.py), over its own
Chroma collection. The home assistant's prompts pillar asks it, and so does
POST /api/prompts/search.

    catalog        the validated library, data/prompts.json
    contribution   prompts and agent proposals from Create (contributions.py)
"""

from __future__ import annotations

from ..retrieval.agent import Candidate, Found, RetrievalAgent, explain
from ..retrieval.index import Doc
from ..retrieval.models import AgentHit
from . import contributions
from .models import Desk, Prompt
from .store import store

agent = RetrievalAgent(
    "prompts",
    "prompt library: validated prompt templates, and prompts and agent proposals colleagues contributed",
)


def text(p: Prompt) -> str:
    """One description per prompt, read alike by Chroma and BM25."""
    parts = [f"{p.title}.", p.description, f"Category: {p.category}."]
    if p.tags:
        parts.append("Tags: " + ", ".join(p.tags) + ".")
    if p.inputs:
        parts.append("Inputs: " + ", ".join(i.label for i in p.inputs) + ".")
    return " ".join(parts)


def sync() -> dict[str, int] | None:
    """The library in the index. Nothing to do unless prompts.json changed."""
    return agent.sync("catalog", [Doc(f"prompt:{p.id}", text(p)) for p in store.library.prompts])


def _hit(p: Prompt, c: Candidate, queries: list[str]) -> AgentHit:
    return AgentHit(
        ref=f"prompt:{p.id}",
        kind="prompt",
        title=p.title,
        summary=p.description,
        href=f"/library/prompts/{p.id}",
        why=explain(c, [p.category, *p.tags], queries),
        meta=f"Rated {p.rating} · {p.uses:,} uses · {p.risk} risk",
        fit=c.fit,
        score=c.score,
        similarity=c.similarity,
        keyword=c.keyword,
    )


def find(
    queries: list[str],
    pool: list[Prompt],
    *,
    desk: Desk | None,
    exclude: set[str] | frozenset[str] = frozenset(),
    rerank_query: str | None = None,
) -> tuple[Found, list[AgentHit]]:
    """What the agent finds among the prompts this person may use (`pool`,
    their entitlement) and the contributions they may see. Their own desk's
    prompts lead at equal fit: it is the work they do."""
    sync()
    who = contributions.viewer()
    contributed = contributions.findable("prompts", who)
    prompts = {f"prompt:{p.id}": p for p in pool}
    allowed = (set(prompts) | set(contributed)) - set(exclude)

    def describe(rid: str) -> str:
        p = prompts.get(rid)
        return f"{p.title}. {p.description} Category: {p.category}." if p else contributions.describe(contributed[rid])

    own_desk = {rid for rid, p in prompts.items() if desk is not None and p.desk == desk.id}
    found = agent.find(queries, allowed, describe=describe, prefer=own_desk, rerank_query=rerank_query)
    hits = [
        _hit(prompts[c.id], c, queries) if c.id in prompts else contributions.hit(contributed[c.id], who, c, queries)
        for c in found.candidates
    ]
    return found, hits
