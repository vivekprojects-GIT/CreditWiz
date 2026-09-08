from typing import Literal

from pydantic import BaseModel

ItemType = Literal["video", "course", "confluence", "guide", "documentation", "quick-reference", "best-practice"]
Status = Literal["not_started", "in_progress", "completed"]


class LearningPath(BaseModel):
    id: str
    title: str
    blurb: str


class Item(BaseModel):
    """One piece of learning content, of any type."""

    id: str
    title: str
    type: ItemType
    description: str
    topics: list[str] = []
    capabilities: list[str] = []
    personas: list[str] = []
    required_for: list[str] = []
    path: str
    level: str = ""
    duration_seconds: int = 0
    tags: list[str] = []
    related_agents: list[str] = []
    url: str = ""
    youtube_id: str = ""
    poster_url: str = ""
    source: str = ""
    # in-app markdown for hub-native content; empty when the item links out
    body: str = ""


class ItemWithProgress(Item):
    status: Status = "not_started"
    progress: int = 0
    required: bool = False


class ItemDetail(ItemWithProgress):
    path_title: str
    related_items: list[ItemWithProgress]
    related_agent_names: dict[str, str]


class Section(BaseModel):
    """A landing-page section. Which sections appear depends on the persona and progress."""

    id: str
    title: str
    subtitle: str = ""
    items: list[ItemWithProgress]


class LearningHome(BaseModel):
    persona: str
    persona_label: str
    paths: list[LearningPath]
    sections: list[Section]
    item_count: int


class ProgressIn(BaseModel):
    item_id: str
    status: Status
    progress: int | None = None


class TopicCoverage(BaseModel):
    """Factual counts only. Deliberately NOT a proficiency score."""

    topic: str
    completed: int
    total: int


class MyLearning(BaseModel):
    persona: str
    persona_label: str
    completed: int
    in_progress: int
    not_started: int
    required_total: int
    required_completed: int
    items: list[ItemWithProgress]
    coverage: list[TopicCoverage]
    proficiency_note: str
