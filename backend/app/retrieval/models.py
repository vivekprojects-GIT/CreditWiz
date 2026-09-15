"""What a pillar agent is asked, and what it answers with."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..hub.models import PillarHit


class AgentSearch(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class AgentHit(PillarHit):
    """A result, with the retrieval signals that placed it."""

    score: float
    similarity: float | None = None
    keyword: float | None = None


class AgentAnswer(BaseModel):
    agent: Literal["prompts", "learning"]
    # The request as the agent searched it: client and deal names removed.
    query: str
    retrieval: Literal["hybrid", "keyword"]
    reranked: bool
    hits: list[AgentHit]
    took_ms: int
