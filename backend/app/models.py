from typing import Literal

from pydantic import BaseModel


class Link(BaseModel):
    label: str
    href: str


class Section(BaseModel):
    title: str
    href: str
    blurb: str


class Pillar(BaseModel):
    id: str
    number: int
    title: str
    short_title: str
    card_title: str = ""
    description: str
    icon: str
    tone: Literal["blue", "teal", "purple"]
    priority: bool = False
    primary_links: list[Link] = []
    secondary_links: list[Link] = []
    cta_label: str
    cta_href: str
    admin_only: bool = False
    sections: list[Section] = []


class PersonaInfo(BaseModel):
    id: str
    label: str
    derived_from: str
    matched_value: str
    rule: str


class CurrentUser(BaseModel):
    id: str
    first_name: str
    display_name: str
    initials: str
    email: str = ""
    job_title: str = ""
    department: str = ""
    business_unit: str = ""
    location: str = ""
    manager: str = ""
    is_admin: bool
    unread_notifications: int
    persona: PersonaInfo


class Domain(BaseModel):
    id: str
    name: str


class Notification(BaseModel):
    id: str
    title: str
    body: str
    href: str
    created_at: str
    read: bool = False


class HomeResponse(BaseModel):
    user: CurrentUser
    domains: list[Domain]
    pillars: list[Pillar]


class SearchResult(BaseModel):
    kind: Literal["solution", "agent", "prompt", "learning"]
    title: str
    href: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
