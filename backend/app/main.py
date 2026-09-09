import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import auth, data, identity
from .account import router as account_router
from .context.router import router as context_router
from .learning.router import router as learning_router
from .marketplace.router import router as marketplace_router
from .marketplace.store import store as marketplace_store
from .models import (
    CurrentUser,
    Domain,
    HomeResponse,
    Notification,
    PersonaInfo,
    Pillar,
    SearchResponse,
    SearchResult,
)
from .permissions import visible


@asynccontextmanager
async def lifespan(app):
    auth.seed_users()
    # Embed the catalogue once at boot. Unchanged agents are skipped, so this is
    # a no-op on every restart after the first unless the catalogue was edited.
    # It never raises: a failed index leaves search on the lexical ranker.
    from .marketplace.semantic import index as semantic_index
    from .marketplace.store import store as agent_store

    counts = semantic_index.sync(agent_store.all_agents)
    if any(counts.values()):
        import logging

        logging.getLogger("mufg.semantic").info("Semantic index synced: %s", counts)
    # Build the ONNX session now, not on the first user's search. Costs
    # nothing if the index is unavailable.
    semantic_index.search("warm up the embedding session", limit=1)
    yield


app = FastAPI(
    title="MUFG AI Hub API", version="0.2.0", lifespan=lifespan
)
app.include_router(auth.router)
app.include_router(account_router)
app.include_router(marketplace_router)
app.include_router(learning_router)
app.include_router(context_router)


def allowed_origins() -> list[str]:
    """Origins allowed to make state-changing calls.

    The hosting platform assigns the public URL at deploy time, so it cannot be
    written into CREDITWIZ_ORIGINS ahead of time. Render exposes it as
    RENDER_EXTERNAL_URL; trust that in addition to whatever is configured.
    """
    origins = [
        o.strip()
        for o in os.environ.get(
            "CREDITWIZ_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]
    external = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if external and external not in origins:
        origins.append(external)
    return origins


@app.middleware("http")
async def session_boundary(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.method == "OPTIONS":
        return await call_next(request)
    origins = allowed_origins()
    if request.method not in ("GET", "HEAD"):
        origin = request.headers.get("origin")
        if (origin and origin not in origins) or request.headers.get(
            "X-CreditWiz-Request"
        ) != "1":
            return JSONResponse(
                {"detail": "Request verification failed"}, status_code=403
            )
    public = request.url.path in (
        "/api/health",
        "/api/auth/options",
        "/api/auth/login",
        "/api/auth/demo",
    )
    uid = auth.resolve_session(request.cookies.get(auth.COOKIE))
    if not public and not uid:
        return JSONResponse({"detail": "Sign in to the MUFG AI Hub"}, status_code=401)
    token = auth.current_id.set(uid)
    profile_token = identity.reset_profile_cache()
    try:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    finally:
        identity.restore(profile_token)
        auth.current_id.reset(token)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
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
        unread_notifications=len([n for n in notifications() if not n.read]),
        demo_mode=not auth.production(),
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
    return [
        Domain(id="all", name="All business domains"),
        *[
            Domain(id=d, name=d)
            for d in sorted(
                {
                    d
                    for a in marketplace_store.agents
                    if visible(a)
                    for d in a.business_domains
                }
            )
        ],
    ]


@app.get("/api/pillars", response_model=list[Pillar])
def pillars() -> list[Pillar]:
    return visible_pillars(current_user())


@app.get("/api/home", response_model=HomeResponse)
def home() -> HomeResponse:
    user = current_user()
    return HomeResponse(
        user=user,
        domains=domains(),
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
    from .database import connect

    with connect() as conn:
        read = {
            r[0]
            for r in conn.execute(
                "SELECT notification_id FROM notification_reads WHERE user_id=?",
                (auth.user_id(),),
            )
        }
    from .account import preferences

    show_learning = preferences().show_learning_reminders
    return [
        n.model_copy(update={"read": n.id in read or n.read})
        for n in data.NOTIFICATIONS
        if show_learning or not n.href.startswith("/learning")
    ]


@app.post("/api/notifications/read")
def mark_notifications_read():
    from .database import connect

    with connect(write=True) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO notification_reads VALUES (?,?)",
            [(auth.user_id(), n.id) for n in data.NOTIFICATIONS],
        )
    return {"ok": True}


@app.get("/api/search", response_model=SearchResponse)
def search(q: str = Query(default="", max_length=200)) -> SearchResponse:
    needle = q.strip().lower()
    if not needle:
        return SearchResponse(query=q, results=[])
    agent_hits = [
        SearchResult(kind="agent", title=a.name, href=f"/marketplace/agents/{a.id}")
        for a in marketplace_store.agents
        if visible(a)
        and (
            needle in a.name.lower()
            or needle in a.tagline.lower()
            or any(needle in t.lower() for t in a.tags)
        )
    ]
    from .learning.router import _load

    _, items = _load()
    learning_hits = [
        SearchResult(kind="learning", title=i.title, href=f"/learning/items/{i.id}")
        for i in items
        if needle == "learning"
        or needle in " ".join([i.title, i.description, *i.topics, *i.tags]).lower()
    ]
    return SearchResponse(query=q, results=(agent_hits + learning_hits)[:20])


# --- built frontend ---------------------------------------------------------
# Every API call in the SPA is a relative /api/... with credentials:'same-origin',
# so the app and the API must share an origin. Serving the build from here keeps
# the session cookie working and removes CORS from the deployment entirely.
# Registered last so every API route is matched first.

def static_root() -> Path:
    """Resolved at request time, not import time, so it is testable and so a
    dev server without a build still starts."""
    return Path(
        os.environ.get(
            "CREDITWIZ_STATIC_DIR",
            Path(__file__).resolve().parents[2] / "frontend" / "dist",
        )
    ).resolve()


@app.get("/{asset_path:path}", include_in_schema=False)
def spa(asset_path: str):
    root = static_root()
    if asset_path.startswith("api/") or not (root / "index.html").is_file():
        raise HTTPException(status_code=404, detail="Not found")
    target = (root / asset_path).resolve()
    # is_relative_to rejects ../ traversal out of the build directory.
    if asset_path and target.is_file() and target.is_relative_to(root):
        # Vite fingerprints filenames under assets/, so those are immutable.
        cache = (
            "public, max-age=31536000, immutable"
            if asset_path.startswith("assets/")
            else "no-cache"
        )
        return FileResponse(target, headers={"Cache-Control": cache})
    # Any other path is a client-side route. index.html must never be cached
    # or a redeploy leaves browsers asking for asset names that are gone.
    return FileResponse(root / "index.html", headers={"Cache-Control": "no-cache"})
