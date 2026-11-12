"""The Learning agent.

Finds courses, videos and guides for a request: the retrieval Discover runs
(retrieval/agent.py), over its own Chroma collection, fed from the learning
catalogue (data/learning.json). The home assistant's learning pillar asks it,
and so does POST /api/learning/search.
"""

from __future__ import annotations

from ..retrieval.agent import Candidate, Found, RetrievalAgent, explain
from ..retrieval.index import Doc
from ..retrieval.models import AgentHit
from .models import Item
from .store import store as catalog_store

agent = RetrievalAgent("learning")

TYPE_LABEL = {
    "video": "Video",
    "course": "Course",
    "guide": "Guide",
    "quick-reference": "Quick reference",
    "best-practice": "Best practice",
    "documentation": "Documentation",
    "confluence": "Confluence page",
}


def text(i: Item) -> str:
    """One description per item, read alike by Chroma and BM25."""
    parts = [f"{i.title}.", i.description]
    for label, values in (("Topics", i.topics), ("Capabilities", i.capabilities), ("Tags", i.tags)):
        if values:
            parts.append(f"{label}: {', '.join(values)}.")
    if i.outcomes:
        parts.append("Teaches: " + "; ".join(i.outcomes) + ".")
    return " ".join(p.strip() for p in parts if p.strip())


def sync() -> dict[str, int] | None:
    """The whole catalogue in the index, hidden items included: who may see
    what is decided per request. Nothing to do unless learning.json changed."""
    _, items = catalog_store.catalog
    return agent.sync("catalog", [Doc(f"learning:{i.id}", text(i)) for i in items])


def _first_sentence(text: str) -> str:
    head = text.split(". ")[0].strip()
    return head if head.endswith(".") else head + "."


def _minutes(seconds: int) -> str:
    m = round(seconds / 60)
    return f"{m} min" if m < 60 else f"{m // 60}h {m % 60}m".replace(" 0m", "")


def _hit(i: Item, c: Candidate, queries: list[str]) -> AgentHit:
    facts = [TYPE_LABEL.get(i.type, i.type), i.source, _minutes(i.duration_seconds) if i.duration_seconds else ""]
    if not i.licensed:
        facts.append("Licence needed")
    return AgentHit(
        ref=f"learning:{i.id}",
        kind="learning",
        title=i.title,
        summary=_first_sentence(i.description),
        href=f"/learning/items/{i.id}",
        why=explain(c, [*i.topics, *i.tags], queries),
        meta=" · ".join(f for f in facts if f),
        score=c.score,
        similarity=c.similarity,
        keyword=c.keyword,
    )


def find(
    queries: list[str],
    pool: list[Item],
    *,
    persona_id: str,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> tuple[Found, list[AgentHit]]:
    """What the agent finds among the items this person may see (`pool`).
    Items mapped to their role lead at equal fit."""
    sync()
    items = {f"learning:{i.id}": i for i in pool}
    allowed = set(items) - set(exclude)

    for_role = {rid for rid, i in items.items() if persona_id in i.personas}
    found = agent.find(queries, allowed, prefer=for_role)
    return found, [_hit(items[c.id], c, queries) for c in found.candidates]
