from typing import Any, Literal

from pydantic import BaseModel, Field

AgentStatus = Literal["production", "pilot", "beta", "in_development", "deprecated"]
AccessType = Literal["open", "request", "restricted"]


class Owner(BaseModel):
    team: str
    name: str = ""
    email: str = ""


class Access(BaseModel):
    type: AccessType = "request"
    how: str = "Contact the owning team for access."
    launch_url: str = ""
    request_url: str = ""


class Agent(BaseModel):
    """Canonical agent metadata. Grouped as in docs/agent-metadata-template.md."""

    # identity
    id: str
    name: str
    tagline: str
    version: str = ""
    # business
    description: str
    problem_solved: str = ""
    business_domains: list[str]
    use_cases: list[str]
    personas: list[str]
    # capabilities
    capabilities: list[str]
    services: list[str] = []
    example_tasks: list[str] = []
    tags: list[str] = []
    category: str
    # technical
    platform: str
    tools_services: list[str] = []
    models: list[str] = []
    architecture_pattern: str = ""
    # governance
    owner: Owner
    status: AgentStatus
    access: Access
    # resources
    documentation_url: str = ""
    architecture_url: str = ""
    # lifecycle
    created_at: str
    updated_at: str
    # curation
    featured: bool = False
    popularity: int = 0


class PersonaInterests(BaseModel):
    domains: list[str] = []
    capabilities: list[str] = []
    tags: list[str] = []


class Persona(BaseModel):
    id: str
    label: str
    description: str
    interests: PersonaInterests


class CarouselRule(BaseModel):
    type: Literal["persona", "category", "featured", "recent"]
    value: str = ""


class CarouselDef(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    rule: CarouselRule


class Carousel(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    agents: list[Agent]


class MarketplaceHome(BaseModel):
    persona: str
    personas: list[Persona]
    domains: list[str]
    carousels: list[Carousel]
    agent_count: int
    example_queries: list[str]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    persona: str | None = None
    domain: str | None = None
    limit: int = Field(default=6, ge=1, le=20)


class AgentMatch(BaseModel):
    agent: Agent
    score: float
    why: str
    reasons: list[str]


class SearchIntent(BaseModel):
    """What we understood from the natural-language query."""

    summary: str
    concepts: list[str] = []
    domains: list[str] = []
    capabilities: list[str] = []
    keywords: list[str] = []


class SearchResponse(BaseModel):
    query: str
    intent: SearchIntent
    engine: Literal["claude", "local"]
    results: list[AgentMatch]
    no_match: bool
    next_steps: list[dict[str, str]] = []


class FeedbackIn(BaseModel):
    context: Literal["search", "agent"]
    helpful: bool
    query: str | None = None
    agent_id: str | None = None
    persona: str | None = None
    missing: str | None = Field(default=None, max_length=2000)


EventType = Literal[
    "search",
    "agent_view",
    "agent_click",
    "agent_launch",
    "request_access",
    "documentation_click",
    "architecture_click",
    "collaborate",
    "feedback_positive",
    "feedback_negative",
]


class EventIn(BaseModel):
    """Interaction footprint. Swim Lane 1 only records these; nothing consumes them yet."""

    type: EventType
    agent_id: str | None = None
    query: str | None = None
    persona: str | None = None
    meta: dict[str, Any] = {}


class Ack(BaseModel):
    ok: bool = True
    id: str
