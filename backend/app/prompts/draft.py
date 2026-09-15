"""Drafting a new prompt from the ones that already passed review.

Deterministic, as the design reference does it: the draft borrows the inputs
of the closest validated prompt and inherits the constraints of up to three, so
what got those prompts through the Data Privacy Office is carried into the new
one. No model writes it, so it costs nothing and cannot invent a rule. Nothing
is saved until the author contributes it.
"""

from __future__ import annotations

import re

from .models import Draft, Prompt, PromptRef
from .store import search, store

_VERB = r"(?:write|draft|create|build|make|compose|design)"
_AUTHORING = re.compile(rf"\b{_VERB}\b", re.I)
_NOUN = re.compile(r"\b(?:prompt|template)s?\b", re.I)
_LEAD = re.compile(r"^\s*(?:(?:can you|could you|please|help me|i want to|i need to)\s+)+", re.I)
_ASK = re.compile(
    rf"\b{_VERB}\s+(?:me\s+)?(?:(?:a|an|the)\s+)?(?:new\s+)?(?:prompt|template)s?\s*"
    r"(?:(?:that|which|to|for|about)\s+)?",
    re.I,
)

_RETURNS = (
    [
        "The main output, structured under clear headings",
        "The figures behind it, each traceable to an input",
        "Anything you could not verify, marked [VERIFY]",
    ],
    [
        "A short executive summary, no more than 200 words",
        "A table of the underlying figures, with the source of each",
        "Two points a reviewer is most likely to challenge",
    ],
)
_MAX_SOURCES = 3
_MAX_CONSTRAINTS = 4


def is_authoring(text: str) -> bool:
    """Someone asking for a prompt to be written, not for one to be found."""
    return bool(_AUTHORING.search(text) and _NOUN.search(text))


def goal_of(text: str) -> str:
    goal = _ASK.sub("", _LEAD.sub("", text), count=1)
    goal = re.sub(r"\s+", " ", goal).strip(" .?!")
    return goal or "complete this task"


def constraints_of(prompt: Prompt) -> list[str]:
    at = prompt.body.find("CONSTRAINTS")
    if at < 0:
        return []
    lines = prompt.body[at:].splitlines()[1:]
    return [line.strip()[1:].strip() for line in lines if line.strip().startswith("-")]


def compose(
    goal: str, *, job_title: str, department: str, variant: bool = False, pool: list[Prompt] | None = None
) -> Draft:
    """A draft for someone in `job_title`, from the validated prompts closest
    to the goal: on their desk first, then across `pool` (the library, or the
    part of it they may see)."""
    prompts = store.library.prompts if pool is None else pool
    desk = store.desk_for(job_title)
    own = [p for p in prompts if desk and p.desk == desk.id]
    sources = [p for _, p in search(goal, own)] or [p for _, p in search(goal, prompts)]
    if not sources:
        sources = sorted(own or prompts, key=lambda p: -p.uses)
    sources = sources[:_MAX_SOURCES]

    seen: set[str] = set()
    constraints: list[str] = []
    for p in sources:
        for c in constraints_of(p):
            key = c.lower()[:28]
            if key not in seen and len(constraints) < _MAX_CONSTRAINTS:
                seen.add(key)
                constraints.append(c)
    if not constraints:
        constraints = ["Reference only figures present in the attachments; never estimate."]

    lead = sources[0]
    role = (job_title or "banker").lower()
    where = f" working in {department}" if department else ""
    task = goal[:1].upper() + goal[1:]
    body = "\n".join(
        [
            f"ROLE: You are a {role} at MUFG{where}.",
            "",
            "INPUT",
            *[f"- {{{{{i.label.upper()}}}}}" for i in lead.inputs[:2]],
            "",
            "TASK",
            f"{task}.",
            *(["Work step by step and show the intermediate figures."] if variant else []),
            "",
            "RETURN",
            *[f"{n}. {r}" for n, r in enumerate(_RETURNS[variant], start=1)],
            "",
            "CONSTRAINTS",
            *[f"- {c}" for c in constraints],
        ]
    )
    words = goal.split()[:6]
    title = " ".join(words)
    return Draft(
        goal=goal,
        title=title[:1].upper() + title[1:],
        description=f"Drafted with the assistant to {goal}.",
        category=lead.category,
        tags=[*lead.tags[:2], "Assistant draft"],
        body=body,
        learned_from=[PromptRef(id=p.id, title=p.title) for p in sources],
        variant=variant,
    )
