from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from ..content_validation import safe_link

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

    _links = field_validator("launch_url", "request_url")(safe_link)


class Agent(BaseModel):
    """Canonical agent metadata. Grouped as in docs/agent-metadata-template.md."""

    # identity
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str
    tagline: str
    version: str = ""
    # business
    description: str
    problem_solved: str = ""
    business_domains: list[str]
    use_cases: list[str]
    # Optional curator hint. Relevance is derived from the business metadata
    # below; naming a persona only amplifies what that metadata already shows.
    personas: list[str] = []
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
    audience_groups: list[str] = ["AI-Hub-Users"]
    active: bool = True
    review_status: Literal["draft", "approved", "retired"] = "approved"
    source_kind: Literal["sample", "enterprise"] = "sample"

    _links = field_validator("documentation_url", "architecture_url")(safe_link)

    @model_validator(mode="after")
    def reviewed_enterprise(self):
        if (
            self.source_kind == "enterprise"
            and not {"audience_groups", "review_status", "active"}
            <= self.model_fields_set
        ):
            raise ValueError(
                "Enterprise agents require explicit ACL and publication metadata"
            )
        return self


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
    # Share of what we understood the user asked for that this agent covers,
    # 0-100. None when nothing structured was extracted, because a percentage of
    # nothing would be an invented number. Deliberately NOT derived from `score`:
    # that is a relative ranking value, so a percentage from it would either
    # always read 100 for the winner or imply a confidence we cannot justify.
    coverage: int | None = None


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
