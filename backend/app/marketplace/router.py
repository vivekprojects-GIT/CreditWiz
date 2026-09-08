from fastapi import APIRouter, HTTPException, Query

from ..context import store as context_store
from . import search
from .models import (
    Ack,
    Agent,
    Carousel,
    EventIn,
    FeedbackIn,
    MarketplaceHome,
    Persona,
    SearchRequest,
    SearchResponse,
)
from .store import store
from ..permissions import resolve_persona

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

EXAMPLE_QUERIES = [
    "I need an agent that can review customer onboarding documents",
    "Screen a new customer against sanctions lists",
    "Summarise a supplier contract and flag unusual clauses",
    "Find assets for a charged-off account",
    "Draft an arrears reminder that follows conduct rules",
    "Review my pull request for security issues",
]

NEXT_STEPS = [
    {"label": "Browse all agents", "href": "/marketplace/agents"},
    {"label": "Learn how to build an agent", "href": "/learning?path=builders"},
    {"label": "Explore the learning catalog", "href": "/learning/catalog"},
]


def _build_carousels(persona: Persona | None) -> list[Carousel]:
    agents = store.agents
    out: list[Carousel] = []
    for c in store.carousels:
        if c.rule.type == "persona":
            items = search.recommend_for_persona(persona, agents)
        elif c.rule.type == "category":
            items = sorted(
                (a for a in agents if a.category == c.rule.value),
                key=lambda a: -a.popularity,
            )
        elif c.rule.type == "featured":
            items = sorted(
                (a for a in agents if a.featured or a.popularity >= 80),
                key=lambda a: -a.popularity,
            )
        else:  # recent
            items = sorted(agents, key=lambda a: a.updated_at, reverse=True)[:8]
        if items:
            out.append(
                Carousel(id=c.id, title=c.title, subtitle=c.subtitle, agents=items)
            )
    return out


def _derived_persona_id() -> str:
    from ..identity import (
        derive_persona,
        load_profile,
    )  # local import avoids a cycle at import time

    return derive_persona(load_profile()).id


@router.get("/home", response_model=MarketplaceHome)
def marketplace_home(
    persona: str | None = Query(default=None), domain: str | None = None
) -> MarketplaceHome:
    p = store.persona(resolve_persona(persona).id)
    carousels = _build_carousels(p)
    if domain:
        carousels = [
            c.model_copy(
                update={"agents": [a for a in c.agents if domain in a.business_domains]}
            )
            for c in carousels
        ]
        carousels = [c for c in carousels if c.agents]
    return MarketplaceHome(
        persona=p.id if p else "",
        personas=store.personas,
        domains=store.domains(),
        carousels=carousels,
        agent_count=len(store.agents),
        example_queries=EXAMPLE_QUERIES,
    )


@router.get("/curation")
def curation(persona: str | None = Query(default=None)) -> dict:
    """Why the 'Recommended for you' row is ordered the way it is.

    Returns the per-component curation score for every agent. Rule-based and
    explainable by design; no behavioural signals are involved.
    """
    p = store.persona(resolve_persona(persona).id)
    rows = []
    for a in store.agents:
        parts = search.curation_breakdown(a, p)
        rows.append(
            {
                "agent_id": a.id,
                "name": a.name,
                "total": round(sum(parts.values()), 2),
                "components": {k: round(v, 2) for k, v in parts.items()},
            }
        )
    rows.sort(key=lambda r: -r["total"])
    return {
        "persona": p.id if p else None,
        "persona_label": p.label if p else None,
        "weights": search.CURATION_WEIGHTS,
        "inputs": ["derived persona", "agent metadata"],
        "excluded": [
            "behavioural footprints (collected, not used for ranking in the MVP)"
        ],
        "ranked": rows,
    }


@router.get("/personas", response_model=list[Persona])
def personas() -> list[Persona]:
    return store.personas


@router.get("/domains", response_model=list[str])
def domains() -> list[str]:
    return store.domains()


@router.get("/agents", response_model=list[Agent])
def list_agents(
    domain: str | None = None,
    category: str | None = None,
    persona: str | None = None,
    status: str | None = None,
) -> list[Agent]:
    items = store.agents
    if domain:
        items = [a for a in items if domain in a.business_domains]
    if category:
        items = [a for a in items if a.category == category]
    if persona:
        items = [a for a in items if persona in a.personas]
    if status:
        items = [a for a in items if a.status == status]
    return sorted(items, key=lambda a: a.name.lower())


@router.get("/agents/{agent_id}", response_model=Agent)
def get_agent(agent_id: str) -> Agent:
    agent = store.agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}/related", response_model=list[Agent])
def related_agents(agent_id: str) -> list[Agent]:
    agent = store.agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    def overlap(other: Agent) -> int:
        return (
            3 * (other.category == agent.category)
            + 2 * len(set(other.business_domains) & set(agent.business_domains))
            + len(set(other.capabilities) & set(agent.capabilities))
        )

    others = [a for a in store.agents if a.id != agent.id]
    return [a for a in sorted(others, key=lambda a: -overlap(a)) if overlap(a) > 0][:3]


@router.post("/search", response_model=SearchResponse)
def nlp_search(req: SearchRequest) -> SearchResponse:
    agents = store.agents
    persona = store.persona(resolve_persona(req.persona).id)
    intent, engine = search.understand(req.query, agents)
    results = search.rank(
        req.query, intent, agents, persona=persona, domain=req.domain, limit=req.limit
    )
    context_store.record_event(
        {
            "pillar": "marketplace",
            "type": "search",
            "query": req.query,
            "persona": persona.id if persona else req.persona,
            "topics": sorted(
                {d for m in results for d in m.agent.business_domains}
                | set(intent.domains)
            ),
            "meta": {"engine": engine, "results": [m.agent.id for m in results]},
        }
    )
    return SearchResponse(
        query=req.query,
        intent=intent,
        engine=engine,
        results=results,
        no_match=not results,
        next_steps=NEXT_STEPS if not results else [],
    )


@router.post("/events", response_model=Ack, deprecated=True)
def post_event(ev: EventIn) -> Ack:
    """Deprecated. Footprints are hub-wide: POST /api/context/events."""
    payload = ev.model_dump()
    payload.setdefault("pillar", "marketplace")
    payload["persona"] = _derived_persona_id()
    payload["subject_id"] = payload.pop("agent_id", None)
    payload["subject_type"] = "agent"
    return Ack(id=context_store.record_event(payload))


@router.post("/feedback", response_model=Ack, deprecated=True)
def post_feedback(fb: FeedbackIn) -> Ack:
    """Deprecated. Feedback is hub-wide: POST /api/context/feedback."""
    payload = fb.model_dump()
    payload.setdefault("pillar", "marketplace")
    payload["persona"] = _derived_persona_id()
    payload["subject_id"] = payload.pop("agent_id", None)
    return Ack(id=context_store.record_feedback(payload))


@router.get("/feedback/summary", deprecated=True)
def feedback_summary() -> dict:
    """Deprecated. Use GET /api/context/summary."""
    return context_store.summary()


@router.get("/metadata-template")
def metadata_template() -> dict:
    return store.metadata_template()


# ---------------------------------------------------------------- docs, architecture, learning

from pathlib import Path as _Path  # noqa: E402

from pydantic import BaseModel as _BaseModel  # noqa: E402

from ..learning.models import ItemWithProgress
from ..learning.router import for_agent as learning_for_agent  # noqa: E402
from .store import _DATA_DIR  # noqa: E402


class DocPage(_BaseModel):
    agent_id: str
    agent_name: str
    title: str
    markdown: str
    source_url: str = ""
    source_kind: str = "sample"


def _read_md(path: _Path) -> str | None:
    if not path.resolve().is_relative_to(_DATA_DIR.resolve()):
        raise HTTPException(404, "Resource not found")
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


@router.get("/agents/{agent_id}/docs", response_model=DocPage)
def agent_docs(agent_id: str) -> DocPage:
    agent = store.agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    md = _read_md(_DATA_DIR / "docs" / f"{agent_id}.md")
    if md is None:
        md = f"# {agent.name} documentation\n\nDocumentation has not been published for this agent yet. Contact **{agent.owner.team}**."
    return DocPage(
        source_kind=agent.source_kind,
        agent_id=agent.id,
        agent_name=agent.name,
        title=f"{agent.name} documentation",
        markdown=md,
        source_url=agent.documentation_url if agent.source_kind == "enterprise" else "",
    )


@router.get("/agents/{agent_id}/architecture", response_model=DocPage)
def agent_architecture(agent_id: str) -> DocPage:
    agent = store.agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    slug = agent.architecture_pattern.lower().replace(" ", "-")
    md = _read_md(_DATA_DIR / "architecture" / f"{slug}.md") if slug else None
    if md is None:
        md = f"# Architecture\n\nNo architecture pattern has been linked for **{agent.name}** yet. Contact **{agent.owner.team}**."
    title = (
        f"{agent.architecture_pattern} pattern"
        if agent.architecture_pattern
        else "Architecture"
    )
    return DocPage(
        source_kind=agent.source_kind,
        agent_id=agent.id,
        agent_name=agent.name,
        title=title,
        markdown=md,
        source_url=agent.architecture_url if agent.source_kind == "enterprise" else "",
    )


@router.get(
    "/agents/{agent_id}/learning",
    response_model=list[ItemWithProgress],
    deprecated=True,
)
def agent_learning(agent_id: str) -> list[ItemWithProgress]:
    """Deprecated. Learning owns learning recommendations: GET /api/learning/for-agent/{agent_id}."""
    if store.agent(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return learning_for_agent(agent_id)
