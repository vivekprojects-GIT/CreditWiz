"""A question put to a pillar agent directly, as Discover's search box puts one
to Discover: POST /api/learning/search."""

from __future__ import annotations

from time import perf_counter
from typing import Callable, Literal

from .agent import Found
from .models import AgentAnswer, AgentHit

# what to search -> what the agent found
Run = Callable[[str], tuple[Found, list[AgentHit]]]


def ask(agent: Literal["learning"], query: str, run: Run) -> AgentAnswer:
    """The guardrails mask the request first, so no index and no log sees a
    client's name. No model reads the request, and the trace keeps the form
    a usage log may hold."""
    from ..context import store as context_store
    from ..hub.guardrails import check, for_retrieval

    started = perf_counter()
    guard = check(query, None)
    searched = for_retrieval(guard.masked, guard.names)
    found, hits = run(searched)
    took_ms = round((perf_counter() - started) * 1000)
    # Enough to reconstruct why this ranking happened: what each retriever
    # proposed and what survived.
    context_store.record_event(
        {
            "pillar": agent,
            "type": "search",
            "query": guard.loggable,
            "meta": {
                "agent": agent,
                "retrieval": found.retrieval,
                "results": [h.ref for h in hits],
                "scores": {h.ref: h.score for h in hits},
                "proposed": found.proposed,
                "embed_ms": found.embed_ms,
            },
        }
    )
    return AgentAnswer(
        agent=agent,
        query=searched,
        retrieval=found.retrieval,
        hits=hits,
        took_ms=took_ms,
    )
