"""Shared user-context API. Every pillar uses these endpoints; none owns them.

ALL 9 PILLARS  ──write──>  /api/context/events, /api/context/feedback
                                    │
                           shared footprint store
                                    │
               /api/context/me  ──read──>  future personalisation
"""

from fastapi import APIRouter, HTTPException

from ..identity import derive_persona, load_profile
from . import store
from .models import (
    Ack,
    ContextSummary,
    EventIn,
    FeedbackIn,
    InterestSignal,
    UserContext,
)

router = APIRouter(prefix="/api/context", tags=["user context"])


@router.post("/events", response_model=Ack)
def post_event(ev: EventIn) -> Ack:
    """Record one interaction footprint from any pillar."""
    if ev.type == "learning_complete":
        raise HTTPException(
            422, "Completion events are recorded by the Learning progress endpoint"
        )
    payload = ev.model_dump()
    payload["persona"] = derive_persona(load_profile()).id
    return Ack(id=store.record_event(payload))


@router.post("/feedback", response_model=Ack)
def post_feedback(fb: FeedbackIn) -> Ack:
    """Record a 'did you find what you needed' answer from any pillar."""
    payload = fb.model_dump()
    payload["persona"] = derive_persona(load_profile()).id
    return Ack(id=store.record_feedback(payload))


@router.get("/me", response_model=UserContext)
def me() -> UserContext:
    """Profile, derived persona and derived interests in one place.

    Interests come from footprints across every pillar. The MVP does not rank on
    them; they show what a cross-pillar personalisation service would consume.
    """
    profile = load_profile()
    persona = derive_persona(profile)
    interests = store.derive_interests()
    evs = store.events()
    return UserContext(
        user_id=profile.id,
        display_name=profile.name,
        job_title=profile.job_title,
        department=profile.department,
        business_unit=profile.business_unit,
        persona=persona.id,
        persona_label=persona.label,
        persona_rule=persona.rule,
        interests=[InterestSignal(**i) for i in interests],
        event_count=len(evs),
        pillars_seen=sorted({e.get("pillar", "hub") for e in evs}),
    )


@router.get("/interests", response_model=list[InterestSignal])
def interests() -> list[InterestSignal]:
    return [InterestSignal(**i) for i in store.derive_interests()]


@router.get("/summary", response_model=ContextSummary)
def summary() -> ContextSummary:
    return ContextSummary(**store.summary())
