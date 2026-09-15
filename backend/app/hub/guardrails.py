"""Security, data and policy guardrails: checked before any model or search runs.

    permissions    what this person may see, in every pillar (entitlements)
    data class     the request's sensitivity: public, internal, client
                   confidential or confidential
    model access   what the approved model may receive for that class, as the
                   data policy says (data/policy.json)
    client data    client and deal names, account numbers and emails found,
                   and masked wherever the policy says so

Masking is one control among these, applied by policy rather than always: if
the policy lets client names go to the approved model, they go as typed.
Searches and usage logs get the masked form whatever the policy says: a client
name is not a word any catalogue holds, and it has no place in a log.

The policy file holds prototype defaults until MUFG's data policy confirms
them, and says so wherever it is applied.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

from ..identity import load_profile
from ..journeys import task
from ..journeys.models import Asset, Sensitivity, Subject
from ..journeys.store import store as journey_store
from ..learning.models import Item
from ..marketplace.models import Agent
from ..permissions import visible
from ..prompts.models import Desk, Prompt
from ..prompts.store import store as prompt_store

ModelAccess = Literal["as_typed", "masked", "none"]
SENSITIVITIES: tuple[Sensitivity, ...] = ("public", "internal", "client_confidential", "confidential")

_DATA_DIR = Path(
    os.environ.get("CREDITWIZ_DATA_DIR", Path(__file__).resolve().parents[2] / "data")
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_ACCOUNT = re.compile(r"\b\d(?:[ -]?\d){7,}\b")
_PLACEHOLDER = re.compile(r"\[(?:CLIENT|DEAL|EMAIL|ACCOUNT)\]")


# ------------------------------------------------------------------ policy


class Policy(BaseModel):
    # What the approved model may receive for a request of each sensitivity.
    model_access: dict[Sensitivity, ModelAccess]
    # Who confirmed this policy. Blank while it holds prototype defaults.
    confirmed_by: str = ""

    @model_validator(mode="after")
    def complete(self):
        missing = [s for s in SENSITIVITIES if s not in self.model_access]
        if missing:
            raise ValueError(f"Data policy has no model access for {', '.join(missing)}")
        return self


@lru_cache(maxsize=4)
def _read(path: str, modified: float) -> Policy:
    return Policy.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def policy() -> Policy:
    """The data policy, re-read when the file changes."""
    path = _DATA_DIR / "policy.json"
    return _read(str(path), path.stat().st_mtime)


# ------------------------------------------------------------- permissions


@dataclass(frozen=True)
class Entitlements:
    """What this person may see, in every pillar. Pillars search only this."""

    agents: list[Agent]
    groups: list[str]
    learning: list[Item]
    assets: list[Asset]
    prompts: list[Prompt]
    desk: Desk | None
    # High-risk prompts from other desks, left out.
    withheld_prompts: int


def entitlements() -> Entitlements:
    from ..learning.router import _load
    from ..marketplace.store import store as agent_store

    profile = load_profile()
    library = prompt_store.library
    desk = prompt_store.desk_for(profile.job_title)
    # The library's own rule for High: restricted to a cleared team.
    prompts = [p for p in library.prompts if p.risk != "High" or (desk is not None and p.desk == desk.id)]
    _, items = _load()
    return Entitlements(
        agents=[a for a in agent_store.agents if visible(a)],
        groups=list(profile.groups),
        learning=items,
        assets=[a for a in journey_store.all_assets.values() if visible(a)],
        prompts=prompts,
        desk=desk,
        withheld_prompts=len(library.prompts) - len(prompts),
    )


# ------------------------------------------------------ data and model access


@dataclass(frozen=True)
class Guard:
    # The request with client and deal names, accounts and emails replaced:
    # what every search and the usage log get.
    masked: str
    subject: Subject | None
    subject_carried_over: bool
    # Every client or deal name found, the conversation's included.
    names: tuple[str, ...]
    # Kinds of identifier found besides names: "email", "account".
    identifiers: tuple[str, ...]
    sensitivity: Sensitivity
    reason: str
    # The policy for this sensitivity, and what it lets the model receive:
    # the request as typed, masked, or nothing at all (None).
    model_access: ModelAccess
    model_view: str | None
    # The only form of the request that may reach usage logs.
    loggable: str
    policy_confirmed: bool


def check(query: str, carried_subject: str | None, rules: Policy | None = None) -> Guard:
    rules = rules or policy()
    found = task.find_subjects(query)
    carried = (carried_subject or "").strip()
    subject = found[0] if found else (Subject(name=carried, kind="client") if carried else None)

    # Identifiers first, so an address at the client's domain goes whole.
    masked, emails = _EMAIL.subn("[EMAIL]", query)
    masked, accounts = _ACCOUNT.subn("[ACCOUNT]", masked)
    identifiers = tuple(kind for kind, n in (("email", emails), ("account", accounts)) if n)
    # Then names, longest first, so "Acme Holdings" goes before "Acme".
    names: dict[str, str] = {s.name: s.kind for s in found}
    if carried and carried.lower() not in (n.lower() for n in names):
        names[carried] = "client"
    for name in sorted(names, key=len, reverse=True):
        masked = re.sub(re.escape(name), f"[{names[name].upper()}]", masked, flags=re.IGNORECASE)

    sensitivity, reason = task.classify_sensitivity(query, subject)
    if sensitivity == "internal" and identifiers:
        sensitivity = "client_confidential"
        reason = "Contains an email address or account number."
    access = rules.model_access[sensitivity]
    return Guard(
        masked=masked,
        subject=subject,
        subject_carried_over=subject is not None and not found,
        names=tuple(names),
        identifiers=identifiers,
        sensitivity=sensitivity,
        reason=reason,
        model_access=access,
        model_view=None if access == "none" else query if access == "as_typed" else masked,
        loggable="[confidential request]" if sensitivity == "confidential" else masked,
        policy_confirmed=bool(rules.confirmed_by),
    )


def stricter(a: Sensitivity, b: Sensitivity | None) -> Sensitivity:
    return a if b is None or SENSITIVITIES.index(a) >= SENSITIVITIES.index(b) else b


def for_retrieval(text: str, names: tuple[str, ...] = ()) -> str:
    """What a search index gets: no client names, typed or as placeholders.
    Neither is a word any catalogue holds; both would only add noise."""
    for name in names:
        text = re.sub(re.escape(name), " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", _PLACEHOLDER.sub("", text)).strip(" ,.;:?!")
