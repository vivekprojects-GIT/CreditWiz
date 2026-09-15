"""The prompt library: validated prompts, the templates new ones start from,
and what people contribute for review.

    desk -> prompts       each validated, with inputs, guidelines, a sample output
    templates             the scaffolds a new prompt starts from
    contributions         prompts, videos and agent proposals awaiting review (SQL)

The library file is demo data from the design reference and every record says
so in source_kind. Contributions are the only part people write.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

Risk = Literal["Low", "Medium", "High"]
# Where a prompt was made, relative to its own desk: the owning team, the wider
# department, or another desk.
Scope = Literal["team", "dept", "other"]
Sort = Literal["relevance", "used", "rated", "new", "saved"]

_ID = r"^[a-z0-9]+$"
_SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class Desk(BaseModel):
    id: str = Field(pattern=_SLUG)
    label: str
    plural: str
    # Directory job titles on this desk. Decides whose prompts show first.
    job_titles: list[str]
    department: str
    teams: dict[Scope, str]


class Person(BaseModel):
    name: str
    initials: str
    team: str


class PromptInput(BaseModel):
    label: str
    type: str
    note: str
    required: bool


class Review(BaseModel):
    name: str
    initials: str
    team: str
    stars: int = Field(ge=1, le=5)
    when: str
    comment: str


class Collaborator(BaseModel):
    name: str
    initials: str
    role: str


class Tutorial(BaseModel):
    title: str
    duration: str
    views: str


class Prompt(BaseModel):
    id: str = Field(pattern=_ID)
    desk: str
    category: str
    scope: Scope
    title: str
    description: str
    tags: list[str]
    views: int = Field(ge=0)
    uses: int = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    ratings: int = Field(ge=0)
    hours_saved: float = Field(ge=0)
    repetition: str
    narrative: str
    contributor: Person
    created: date
    updated: date
    validated: bool
    risk: Risk
    risk_note: str
    tutorial: Tutorial | None = None
    inputs: list[PromptInput]
    guidelines: list[str]
    body: str
    sample_output: str
    reviews: list[Review] = []
    collaborators: list[Collaborator] = []
    source_kind: Literal["sample", "enterprise"] = "sample"


class Template(BaseModel):
    id: str = Field(pattern=_ID)
    name: str
    use: str
    when: str
    body: str


class Library(BaseModel):
    categories: list[str]
    desks: list[Desk]
    risk_levels: dict[Risk, str]
    templates: list[Template]
    prompts: list[Prompt]

    @model_validator(mode="after")
    def consistent(self):
        desks = {d.id for d in self.desks}
        ids = [p.id for p in self.prompts]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate prompt id")
        for p in self.prompts:
            if p.desk not in desks:
                raise ValueError(f"{p.id}: unknown desk {p.desk}")
            if p.category not in self.categories:
                raise ValueError(f"{p.id}: unknown category {p.category}")
        return self


# ---------------------------------------------------------------- responses


class DeskRef(BaseModel):
    id: str
    label: str


class PromptCard(BaseModel):
    id: str
    desk: DeskRef
    category: str
    title: str
    description: str
    tags: list[str]
    # Where it was made relative to the viewer: their team, their department,
    # or elsewhere. Everything on another desk is "other".
    relation: Scope
    uses: int
    rating: float
    ratings: int
    hours_saved: float
    risk: Risk
    validated: bool
    contributor: Person
    updated: date
    saved: bool = False
    source_kind: Literal["sample", "enterprise"]


class LibraryPage(BaseModel):
    # The viewer's desk; None when their job title is on no desk.
    desk: DeskRef | None
    # The desk shown, or "all".
    showing: str
    desks: list[DeskRef]
    categories: list[str]
    total: int
    prompts: list[PromptCard]


class PromptDetail(PromptCard):
    views: int
    repetition: str
    narrative: str
    created: date
    risk_note: str
    tutorial: Tutorial | None
    inputs: list[PromptInput]
    guidelines: list[str]
    body: str
    sample_output: str
    reviews: list[Review]
    collaborators: list[Collaborator]
    related: list[PromptCard]


class PromptRef(BaseModel):
    id: str
    title: str


class DraftRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=300)
    variant: bool = False


class Draft(BaseModel):
    """A prompt written for someone from the validated ones. Not saved."""

    goal: str
    title: str
    description: str
    category: str
    tags: list[str]
    body: str
    # The validated prompts whose inputs and constraints it carries.
    learned_from: list[PromptRef]
    # False: the main output. True: the version that shows its workings.
    variant: bool


# ------------------------------------------------------------ contributions

_Text = Annotated[str, Field(min_length=1, max_length=400)]


class Safety(BaseModel):
    """The author's data safety declaration, as the review asks it."""

    client_data: bool
    mnpi: bool
    feeds_control: bool


class PromptSubmission(BaseModel):
    kind: Literal["prompt"]
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    category: str
    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(default=[], max_length=5)
    scope: Scope = "team"
    body: str = Field(min_length=1, max_length=20000)
    inputs: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(default=[], max_length=12)
    hours_saved: float | None = Field(default=None, ge=0, le=100)
    safety: Safety
    guidelines: list[_Text] = Field(default=[], max_length=12)
    # The author confirms they tested it at least three times.
    tested: Literal[True]
    # Validated prompts an assistant draft was built from.
    learned_from: list[str] = Field(default=[], max_length=5)


class VideoSubmission(BaseModel):
    kind: Literal["video"]
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    # The recording's file name. The prototype stores no media.
    recording: str = Field(default="", max_length=200)


class AgentSubmission(BaseModel):
    kind: Literal["agent"]
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    # Validated prompts to chain, in the order they run.
    chain: list[str] = Field(min_length=1, max_length=8)


Submission = Annotated[
    PromptSubmission | VideoSubmission | AgentSubmission, Field(discriminator="kind")
]

ContributionKind = Literal["prompt", "video", "agent"]
ContributionStatus = Literal["in_review", "live", "returned"]
# Who may find it once approved; its author can from the moment it is submitted.
Audience = Literal["team", "department", "everyone"]


class Contribution(BaseModel):
    id: str
    kind: ContributionKind
    title: str
    description: str
    status: ContributionStatus
    # Who reviews it, and what happens next.
    review: str
    # For a prompt: the risk rating its safety declaration implies.
    risk: Risk | None = None
    audience: Audience
    created_at: str


class ReviewDecision(BaseModel):
    decision: Literal["live", "returned"]
