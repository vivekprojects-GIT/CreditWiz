"""Shared user-context models for the whole AI Hub.

This layer is horizontal: every pillar writes the same event and feedback shapes
here. No pillar owns it. Swim Lane 1 is only one producer among nine.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# The nine pillars, plus the hub shell itself.
Pillar = Literal[
    "marketplace",
    "prompts",
    "learning",
    "intake",
    "governance",
    "knowledge",
    "community",
    "insights",
    "platform",
    "hub",
]

# Event vocabulary shared across pillars. Pillar-specific nouns stay in `meta`.
EventType = Literal[
    "search",
    "view",
    "click",
    "launch",
    "request_access",
    "documentation_click",
    "architecture_click",
    "collaborate",
    "learning_view",
    "learning_complete",
    "feedback_positive",
    "feedback_negative",
    # legacy marketplace names, still accepted so older clients keep working
    "agent_view",
    "agent_click",
    "agent_launch",
]


class EventIn(BaseModel):
    """One interaction footprint, written by any pillar."""

    pillar: Pillar
    type: EventType
    subject_id: str | None = Field(default=None, description="Agent id, video id, prompt id, thread id …")
    subject_type: str | None = Field(default=None, description="agent | video | prompt | policy | thread …")
    query: str | None = None
    persona: str | None = None
    topics: list[str] = Field(default_factory=list, description="Tags/domains this interaction touched.")
    meta: dict[str, Any] = {}


class FeedbackIn(BaseModel):
    pillar: Pillar
    context: str = Field(description="Where the question was asked: search, agent, video …")
    helpful: bool
    subject_id: str | None = None
    query: str | None = None
    persona: str | None = None
    missing: str | None = Field(default=None, max_length=2000)


class Ack(BaseModel):
    ok: bool = True
    id: str


class InterestSignal(BaseModel):
    topic: str
    weight: float
    events: int
    pillars: list[str]


class UserContext(BaseModel):
    """What the hub knows about a user, assembled from profile + footprints.

    `interests` is derived from collected events and is NOT used for ranking in the
    MVP. It exists to show the seam a future personalisation service reads from.
    """

    user_id: str
    display_name: str
    job_title: str
    department: str
    business_unit: str
    persona: str
    persona_label: str
    persona_rule: str
    interests: list[InterestSignal]
    event_count: int
    pillars_seen: list[str]


class PillarActivity(BaseModel):
    pillar: str
    events: int
    types: dict[str, int]


class ContextSummary(BaseModel):
    total_events: int
    total_feedback: int
    helpful: int
    not_helpful: int
    by_pillar: list[PillarActivity]
    recent_missing: list[str]
