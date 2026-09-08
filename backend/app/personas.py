"""Personas are hub-level, not owned by any pillar.

Both the Marketplace (agent curation) and Learning (learning curation) rank against
the same persona definitions, so they live here rather than inside either pillar.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pydantic import BaseModel

_DATA_DIR = Path(os.environ.get("CREDITWIZ_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))

_ALIASES = {
    "business user": "business_user",
    "business": "business_user",
    "compliance user": "compliance_user",
    "compliance": "compliance_user",
    "risk analyst": "risk_analyst",
    "risk": "risk_analyst",
    "operations user": "operations_user",
    "operations": "operations_user",
    "ops": "operations_user",
    "developer": "developer",
    "engineer": "developer",
}


class PersonaInterests(BaseModel):
    domains: list[str] = []
    capabilities: list[str] = []
    tags: list[str] = []


class Persona(BaseModel):
    id: str
    label: str
    description: str
    interests: PersonaInterests


def persona_id(value: str) -> str:
    """Accept either an id ('compliance_user') or a label ('Compliance User')."""
    key = value.strip().lower().replace("_", " ")
    if key in _ALIASES:
        return _ALIASES[key]
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def all_personas() -> list[Persona]:
    with open(_DATA_DIR / "personas.json", encoding="utf-8") as fh:
        return [Persona.model_validate(p) for p in json.load(fh)]


def get(value: str | None) -> Persona | None:
    if not value:
        return None
    pid = persona_id(value)
    return next((p for p in all_personas() if p.id == pid), None)
