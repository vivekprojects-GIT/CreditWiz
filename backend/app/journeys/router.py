"""Journeys API: what a persona does, and what helps at each job.

    GET /api/journeys           the signed-in persona's jobs
    GET /api/journeys/{id}      one job: steps, systems of record, what helps

The home assistant that answers from these journeys is hub/ (POST /api/ask).
"""

from fastapi import APIRouter, HTTPException

from ..permissions import resolve_persona
from .models import INTENTS, Journey, JourneyPage, JourneysHome, JourneySummary
from .store import CardBuilder, store

router = APIRouter(tags=["journeys"])


def summary(journey: Journey, cards: CardBuilder) -> JourneySummary:
    return JourneySummary(
        id=journey.id,
        title=journey.title,
        summary=journey.summary,
        systems=[s.system for s in journey.systems],
        asset_count=len(cards.cards(journey.assets)),
    )


@router.get("/api/journeys", response_model=JourneysHome)
def journeys(persona: str | None = None) -> JourneysHome:
    p = resolve_persona(persona)
    found = store.for_persona(p.id)
    cards = CardBuilder()
    return JourneysHome(
        persona=p.id,
        persona_label=p.label,
        examples=found.examples if found else [],
        journeys=[summary(j, cards) for j in found.journeys] if found else [],
    )


@router.get("/api/journeys/{journey_id}", response_model=JourneyPage)
def journey(journey_id: str, persona: str | None = None) -> JourneyPage:
    found = store.journey(journey_id)
    if found is None:
        raise HTTPException(404, "Journey not found")
    owner_persona, j = found
    p = resolve_persona(persona)
    label = p.label if p.id == owner_persona else owner_persona
    cards = CardBuilder().cards(j.assets)
    cards.sort(key=lambda c: INTENTS.index(c.intent))
    return JourneyPage(
        id=j.id,
        persona=owner_persona,
        persona_label=label,
        title=j.title,
        summary=j.summary,
        steps=j.steps,
        systems=j.systems,
        assets=cards,
    )
