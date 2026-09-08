from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# backend/.env holds ANTHROPIC_API_KEY and optional CREDITWIZ_* settings.
# Real environment variables win over the file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from . import data, identity  # noqa: E402
from .context.router import router as context_router
from .learning.router import router as learning_router
from .marketplace.router import router as marketplace_router
from .marketplace.store import store as marketplace_store
from .models import CurrentUser, Domain, HomeResponse, Notification, PersonaInfo, Pillar, SearchResponse, SearchResult

app = FastAPI(title="CreditWiz Enterprise AI Hub API", version="0.1.0")
app.include_router(marketplace_router)
app.include_router(learning_router)
app.include_router(context_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user() -> CurrentUser:
    """Directory profile + derived persona. Persona is never stored on the profile."""
    profile = identity.load_profile()
    persona = identity.derive_persona(profile)
    return CurrentUser(
        id=profile.id,
        first_name=profile.first_name,
        display_name=profile.name,
        initials=profile.initials,
        email=profile.email,
        job_title=profile.job_title,
        department=profile.department,
        business_unit=profile.business_unit,
        location=profile.location,
        manager=profile.manager,
        is_admin=identity.is_admin(profile),
        unread_notifications=len([n for n in data.NOTIFICATIONS if not n.read]),
        persona=PersonaInfo(**persona.model_dump()),
    )


def visible_pillars(user: CurrentUser) -> list[Pillar]:
    return [p for p in data.PILLARS if user.is_admin or not p.admin_only]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me", response_model=CurrentUser)
def me() -> CurrentUser:
    return current_user()


@app.get("/api/domains", response_model=list[Domain])
def domains() -> list[Domain]:
    return data.DOMAINS


@app.get("/api/pillars", response_model=list[Pillar])
def pillars() -> list[Pillar]:
    return visible_pillars(current_user())


@app.get("/api/home", response_model=HomeResponse)
def home() -> HomeResponse:
    user = current_user()
    return HomeResponse(
        user=user,
        domains=data.DOMAINS,
        pillars=visible_pillars(user),
    )


@app.get("/api/pillars/{pillar_id}", response_model=Pillar)
def pillar(pillar_id: str) -> Pillar:
    for p in visible_pillars(current_user()):
        if p.id == pillar_id:
            return p
    raise HTTPException(status_code=404, detail="Pillar not found")


@app.get("/api/notifications", response_model=list[Notification])
def notifications() -> list[Notification]:
    return data.NOTIFICATIONS


@app.get("/api/search", response_model=SearchResponse)
def search(q: str = Query(default="", max_length=200)) -> SearchResponse:
    needle = q.strip().lower()
    if not needle:
        return SearchResponse(query=q, results=[])
    agent_hits = [
        SearchResult(kind="agent", title=a.name, href=f"/marketplace/agents/{a.id}")
        for a in marketplace_store.agents
        if needle in a.name.lower() or needle in a.tagline.lower() or any(needle in t for t in a.tags)
    ]
    other_hits = [r for r in data.SEARCH_INDEX if r.kind != "agent" and (needle in r.title.lower() or needle in r.kind)]
    return SearchResponse(query=q, results=(agent_hits + other_hits)[:8])
