"""Visibility is independent of recommendation relevance or persona previews."""

from fastapi import HTTPException

from . import personas
from .identity import derive_persona, is_admin, load_profile


def visible(record) -> bool:
    profile = load_profile()
    return (
        record.active
        and record.review_status == "approved"
        and bool(set(profile.groups) & set(record.audience_groups))
    )


def resolve_persona(value: str | None = None):
    profile = load_profile()
    derived = derive_persona(profile).id
    result = personas.get(value or derived)
    if result is None:
        raise HTTPException(422, "Unknown persona")
    if result.id != derived and not is_admin(profile):
        raise HTTPException(
            403, "Persona preview is available to hub administrators only"
        )
    return result
