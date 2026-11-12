"""Which connected systems are live for this person, and what blocks the rest.

When a system is not live Nexus still works, on sample content, and this is
where it says exactly which credential or permission is missing, in words an
MUFG administrator can act on. Errors are the systems' own short reasons
(an AADSTS code, an HTTP status); never a token or anything a person wrote.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from . import auth, entra
from .http import ExternalError

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

State = Literal["live", "sample", "signed_out", "blocked", "not_configured"]
EVERYONE = "*"

_errors: dict[tuple[str, str], tuple[str, float]] = {}
_lock = threading.Lock()


def explain(error: ExternalError) -> str:
    said = f"{error.service} returned {error.status}" if error.status else f"{error.service} did not respond"
    return f"{said}: {error.detail}" if error.detail else said


def record_error(integration: str, user_id: str | None, detail: str) -> None:
    with _lock:
        _errors[(integration, user_id or EVERYONE)] = (detail, time.time())


def clear_error(integration: str, user_id: str | None) -> None:
    with _lock:
        _errors.pop((integration, user_id or EVERYONE), None)


def last_error(integration: str, user_id: str | None) -> str:
    with _lock:
        found = _errors.get((integration, user_id or EVERYONE))
    return found[0] if found else ""


class Need(BaseModel):
    what: str
    # The environment setting that carries it, when there is one.
    setting: str = ""
    met: bool


class Doc(BaseModel):
    label: str
    url: str


class Integration(BaseModel):
    id: str
    name: str
    state: State
    summary: str
    # The system's own reason for the last failure, when there was one.
    blocking: str = ""
    needs: list[Need]
    # What Nexus calls once it is live.
    calls: list[str]
    # Where the integration lives in the code.
    code: str
    docs: list[Doc]


def _set(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _entra(uid: str | None) -> Integration:
    configured = entra.configured()
    signed_in = entra.signed_in(uid)
    # A sign-in that failed before anyone was signed in is kept for everyone.
    blocking = last_error("entra", uid) or last_error("entra", None)
    state: State = "blocked" if blocking else "live" if signed_in else "signed_out" if configured else "not_configured"
    summary = {
        "live": "You are signed in with your Microsoft account. Nexus holds your tokens on the server only.",
        "signed_out": "Ready. Sign in with Microsoft to let Nexus call Microsoft 365 as you.",
        "not_configured": "Not set up. Nexus needs MUFG's app registration in Microsoft Entra ID.",
        "blocked": "Sign-in failed. The reason Microsoft gave is below.",
        "sample": "",
    }[state]
    return Integration(
        id="entra",
        name="Microsoft Entra ID sign-in",
        state=state,
        summary=summary,
        blocking=blocking,
        needs=[
            Need(what="Directory (tenant) ID of MUFG's Entra tenant", setting="ENTRA_TENANT_ID", met=_set("ENTRA_TENANT_ID")),
            Need(what="Application (client) ID of an app registration for Nexus", setting="ENTRA_CLIENT_ID", met=_set("ENTRA_CLIENT_ID")),
            Need(what="A client secret for that app registration", setting="ENTRA_CLIENT_SECRET", met=_set("ENTRA_CLIENT_SECRET")),
            Need(
                what=f"Redirect URI {entra.redirect_uri()} added to the app registration (Web platform)",
                setting="ENTRA_REDIRECT_URI",
                met=configured,
            ),
            Need(what="Delegated Microsoft Graph permission User.Read", met=signed_in),
        ],
        calls=[
            "GET https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize (sign-in, with PKCE)",
            "POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token (code for tokens)",
            "GET https://graph.microsoft.com/v1.0/me (name, job title, department for the persona)",
        ],
        code="backend/app/entra.py",
        docs=[
            Doc(label="Entra: OpenID Connect", url="https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc"),
            Doc(label="Entra: ID token claims", url="https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference"),
            Doc(label="Graph: get user", url="https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0"),
        ],
    )


def _pluralsight() -> Integration:
    from .learning import pluralsight

    blocking = last_error("pluralsight", None)
    state: State = "blocked" if blocking else "live" if pluralsight.configured() else "sample"
    summary = {
        "live": "Course details and progress come live from Pluralsight's API.",
        "blocked": "Pluralsight refused the last call, so Learning is showing the catalogue's sample values. The reason is below.",
        "sample": "Learning shows the catalogue's sample Pluralsight courses. A course opens as a Pluralsight search.",
        "signed_out": "",
        "not_configured": "",
    }[state]
    return Integration(
        id="pluralsight",
        name="Pluralsight",
        state=state,
        summary=summary,
        blocking=blocking,
        needs=[
            Need(what="API access enabled on MUFG's Pluralsight plan", met=state == "live"),
            Need(what="An API key from MUFG's Pluralsight plan administrator", setting="PLURALSIGHT_API_KEY", met=pluralsight.configured()),
            Need(what="MUFG's Pluralsight single-sign-on organisation name, for course links", setting="PLURALSIGHT_SSO_ORG", met=_set("PLURALSIGHT_SSO_ORG")),
        ],
        calls=[
            "POST https://paas-api.pluralsight.com/graphql courseCatalog (course details, and search with searchTerm)",
            "POST https://paas-api.pluralsight.com/graphql users, courseProgress (the learner's progress)",
            "https://app.pluralsight.com/sso/{org}?returnUrl=library/courses/{slug} (Start course)",
        ],
        code="backend/app/learning/pluralsight.py",
        docs=[
            Doc(label="Pluralsight: Using GraphQL", url="https://developer.pluralsight.com/docs/getting-started/using-graphql"),
            Doc(label="Pluralsight: courseCatalog", url="https://developer.pluralsight.com/schema/content/courseCatalog"),
            Doc(label="Pluralsight: courseProgress", url="https://developer.pluralsight.com/schema/usage/courseProgress"),
            Doc(label="Pluralsight: SSO links", url="https://help.pluralsight.com/hc/en-us/articles/24395488712340-Creating-SSO-enabled-links"),
        ],
    )


def _leap() -> Integration:
    # No connection exists yet: how Leap is read (an API or an export) is MUFG L&D's to confirm.
    return Integration(
        id="leap",
        name="Leap",
        state="sample",
        summary="Learning shows the catalogue's sample Leap courses. Leap is not connected yet.",
        needs=[Need(what="Leap's access method from MUFG L&D: an API or an export file", met=False)],
        calls=[],
        code="",
        docs=[],
    )


def _microsoft_learn() -> Integration:
    blocking = last_error("microsoft_learn", None)
    state: State = "blocked" if blocking else "live"
    return Integration(
        id="microsoft_learn",
        name="Microsoft Learn",
        state=state,
        summary=(
            "Microsoft Learn didn't answer the last call. The reason is below."
            if blocking
            else "Live. Search and read Learn modules in Nexus through Microsoft's public Learn MCP server; no credentials needed."
        ),
        blocking=blocking,
        needs=[Need(what="Outbound HTTPS from Nexus to learn.microsoft.com", met=not blocking)],
        calls=[
            "POST https://learn.microsoft.com/api/mcp microsoft_docs_search (search Learn)",
            "POST https://learn.microsoft.com/api/mcp microsoft_docs_fetch (read a module or unit as markdown)",
        ],
        code="backend/app/learning/mslearn.py",
        docs=[
            Doc(label="Learn MCP: developer reference", url="https://learn.microsoft.com/en-us/training/support/mcp-developer-reference"),
        ],
    )


@router.get("", response_model=list[Integration])
def status() -> list[Integration]:
    uid = auth.current_id.get()
    return [_entra(uid), _leap(), _pluralsight(), _microsoft_learn()]
