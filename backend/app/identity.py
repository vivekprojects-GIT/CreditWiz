"""Who is signed in, and which persona the hub derives for them.

    Directory / user profile        (mocked in data/user.json for the MVP)
            ↓
    role + department + business unit
            ↓
    persona mapping                 (data/persona-mapping.json)
            ↓
    derived persona                 -> curation, search boosts, recommendations

The profile deliberately has no persona field. When Active Directory is wired in,
replace `load_profile()`; the mapping and everything downstream stay the same.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from . import personas as hub_personas

_DATA_DIR = Path(os.environ.get("CREDITWIZ_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))


class DirectoryProfile(BaseModel):
    id: str
    name: str
    first_name: str
    initials: str
    email: str = ""
    job_title: str = ""
    department: str = ""
    business_unit: str = ""
    location: str = ""
    manager: str = ""
    groups: list[str] = []


class DerivedPersona(BaseModel):
    id: str
    label: str
    derived_from: Literal["role", "department", "business_unit", "default"]
    matched_value: str
    rule: str


def _read(name: str) -> dict:
    with open(_DATA_DIR / name, encoding="utf-8") as fh:
        raw = json.load(fh)
    raw.pop("$comment", None)
    return raw


def load_profile() -> DirectoryProfile:
    return DirectoryProfile.model_validate(_read("user.json"))


def load_mapping() -> dict:
    return _read("persona-mapping.json")


def _label(persona_id: str) -> str:
    return next((p.label for p in hub_personas.all_personas() if p.id == persona_id), persona_id)


def derive_persona(profile: DirectoryProfile, mapping: dict | None = None) -> DerivedPersona:
    m = mapping or load_mapping()
    by_role: dict[str, str] = m.get("by_role", {})
    by_dept: dict[str, str] = m.get("by_department", {})
    title = profile.job_title.strip()
    title_l = title.lower()

    # 1. exact job title
    for role, persona in by_role.items():
        if role.lower() == title_l:
            pid = hub_personas.persona_id(persona)
            return DerivedPersona(id=pid, label=_label(pid), derived_from="role", matched_value=title, rule=f'job title = "{role}"')
    # 2. job title contains a mapped role (e.g. "Senior Compliance Analyst")
    for role, persona in sorted(by_role.items(), key=lambda kv: -len(kv[0])):
        if role.lower() in title_l:
            pid = hub_personas.persona_id(persona)
            return DerivedPersona(id=pid, label=_label(pid), derived_from="role", matched_value=title, rule=f'job title contains "{role}"')
    # 3. department, 4. business unit
    for source, value in (("department", profile.department), ("business_unit", profile.business_unit)):
        v_l = value.strip().lower()
        for dept, persona in sorted(by_dept.items(), key=lambda kv: -len(kv[0])):
            if v_l and (dept.lower() == v_l or dept.lower() in v_l):
                pid = hub_personas.persona_id(persona)
                return DerivedPersona(id=pid, label=_label(pid), derived_from=source, matched_value=value, rule=f'{source.replace("_", " ")} matches "{dept}"')  # type: ignore[arg-type]
    pid = hub_personas.persona_id(m.get("default", "Business User"))
    return DerivedPersona(id=pid, label=_label(pid), derived_from="default", matched_value="", rule="no mapping matched; hub default")


def is_admin(profile: DirectoryProfile, mapping: dict | None = None) -> bool:
    m = mapping or load_mapping()
    return any(g in profile.groups for g in m.get("admin_groups", []))
