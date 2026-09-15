"""The Prompts & Skills and Learning agents, and what Create puts into them."""

import pytest
from fastapi.testclient import TestClient

from app import database
from app.hub import llm
from app.learning import agent as learning_agent
from app.main import app
from app.prompts import agent as prompts_agent
from app.prompts.contributions import reindex
from app.prompts.store import store

client = TestClient(app)

# The demo account on each desk of the library.
DESK_USER = {"relationship-manager": "demo-rm", "credit-analyst": "demo-credit", "risk-analyst": "demo-risk"}

PROMPT = {
    "kind": "prompt",
    "title": "Teaser screening note for leveraged deals",
    "description": "Turns a leveraged finance teaser into a one-page screening note.",
    "category": "Corporate Banking",
    "tags": ["Screening", "Leveraged finance"],
    "scope": "team",
    "body": "ROLE: You are a leveraged finance banker at MUFG.",
    "inputs": ["Deal teaser"],
    "hours_saved": 2,
    "safety": {"client_data": False, "mnpi": False, "feeds_control": False},
    "guidelines": [],
    "tested": True,
    "learned_from": [],
}


def _as(user_id: str) -> None:
    client.cookies.clear()
    assert client.post("/api/auth/demo", json={"user_id": user_id}).status_code == 200


def _ask(path: str, query: str) -> dict:
    response = client.post(path, json={"query": query})
    assert response.status_code == 200, response.text
    return response.json()


def _refs(answer: dict) -> list[str]:
    return [h["ref"] for h in answer["hits"]]


def _submit(**changes) -> dict:
    response = client.post("/api/contributions", json={**PROMPT, **changes})
    assert response.status_code == 201, response.text
    return response.json()


def _review(contribution_id: str, decision: str):
    return client.post(f"/api/contributions/{contribution_id}/review", json={"decision": decision})


# ---------------------------------------------------------------- retrieval


def test_the_prompts_agent_finds_a_prompt_by_what_it_is_for():
    _as("demo-credit")
    answer = _ask("/api/prompts/search", "check whether a borrower breached its loan agreement terms")
    assert answer["retrieval"] == "hybrid"
    best = answer["hits"][0]
    assert best["title"] == "Covenant compliance monitor"
    assert best["similarity"] is not None and best["keyword"] is not None


def test_the_learning_agent_finds_courses_by_what_they_teach():
    answer = _ask("/api/learning/search", "learn prompt engineering")
    assert answer["retrieval"] == "hybrid"
    assert "4 Methods of Prompt Engineering" in [h["title"] for h in answer["hits"]]
    assert all(r.startswith("learning:") for r in _refs(answer))


@pytest.mark.parametrize("nonsense", ["zebra origami", "best pizza near me", "tell me a joke"])
def test_nonsense_finds_nothing_in_either_agent(nonsense):
    assert _ask("/api/prompts/search", nonsense)["hits"] == []
    assert _ask("/api/learning/search", nonsense)["hits"] == []


def test_a_high_risk_prompt_is_only_ever_retrieved_for_its_own_desk():
    high = next(p for p in store.library.prompts if p.risk == "High")
    other = next(user for desk, user in DESK_USER.items() if desk != high.desk)
    _as(other)
    assert f"prompt:{high.id}" not in _refs(_ask("/api/prompts/search", high.title))
    _as(DESK_USER[high.desk])
    assert f"prompt:{high.id}" in _refs(_ask("/api/prompts/search", high.title))


def test_an_agent_retrieves_only_from_what_it_is_handed():
    wanted = store.library.prompts[0]
    pool = [p for p in store.library.prompts if p.id != wanted.id]
    _, hits = prompts_agent.find([wanted.title], pool, desk=None)
    assert f"prompt:{wanted.id}" not in [h.ref for h in hits]


def test_a_client_name_reaches_no_index_and_no_log():
    _as("demo-rm")
    answer = _ask("/api/prompts/search", "pitch deck outline for Acme Holdings")
    assert "Acme" not in answer["query"]
    assert "Corporate pitch structurer" in [h["title"] for h in answer["hits"]]
    with database.connect() as conn:
        logged = [r["payload"] for r in conn.execute("SELECT payload FROM events")]
    assert logged and not any("Acme" in p for p in logged)


def test_the_model_orders_the_shortlist_and_loses_nothing(monkeypatch):
    shown = {}

    def rerank(what, request, candidates):
        shown["ids"] = [rid for rid, _ in candidates]
        # A reply that judges only one candidate.
        return [(shown["ids"][-1], "strong")]

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "rerank", rerank)
    _as("demo-credit")
    answer = _ask("/api/prompts/search", "write a credit memo")
    assert answer["reranked"] is True
    assert len(shown["ids"]) > 1
    assert _refs(answer) == [shown["ids"][-1], *shown["ids"][:-1]]


def test_the_model_grades_every_candidate_and_what_does_not_fit_is_dropped(monkeypatch):
    shown = {}

    def rerank(what, request, candidates):
        ids = shown["ids"] = [rid for rid, _ in candidates]
        return [(ids[0], "partial"), (ids[1], "strong"), *((rid, "none") for rid in ids[2:])]

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "rerank", rerank)
    _as("demo-credit")
    answer = _ask("/api/prompts/search", "write a credit memo")
    assert len(shown["ids"]) >= 3
    # Strong before partial; no fit is not shown at all.
    assert _refs(answer) == [shown["ids"][1], shown["ids"][0]]
    assert [h["fit"] for h in answer["hits"]] == ["strong", "partial"]


# ----------------------------------------------------------------- ingestion


def test_create_embeds_a_prompt_into_the_prompts_index_with_its_author():
    _as("demo-rm")
    c = _submit()
    stored = prompts_agent.agent.semantic.stored(f"contribution:{c['id']}")
    assert stored is not None
    assert stored["owner"] == "demo-rm" and stored["source"] == "contribution"
    assert learning_agent.agent.semantic.stored(f"contribution:{c['id']}") is None


def test_create_embeds_a_skill_video_into_the_learning_index():
    _as("demo-rm")
    response = client.post(
        "/api/contributions",
        json={
            "kind": "video",
            "title": "Reconciling nostro breaks with the Secure LLM",
            "description": "A walkthrough of matching unreconciled nostro items.",
            "recording": "nostro.mp4",
        },
    )
    c = response.json()
    assert c["audience"] == "everyone"
    assert learning_agent.agent.semantic.stored(f"contribution:{c['id']}")["owner"] == "demo-rm"
    assert prompts_agent.agent.semantic.stored(f"contribution:{c['id']}") is None
    assert f"contribution:{c['id']}" in _refs(_ask("/api/learning/search", "reconciling nostro breaks"))


def test_its_author_finds_it_at_once_and_everyone_else_once_approved():
    _as("demo-rm")
    c = _submit(scope="other")
    ref = f"contribution:{c['id']}"
    mine = next(h for h in _ask("/api/prompts/search", PROMPT["title"])["hits"] if h["ref"] == ref)
    assert mine["meta"] == "Your prompt · In review"
    assert mine["href"] == "/library/mine"

    _as("demo-credit")
    assert ref not in _refs(_ask("/api/prompts/search", PROMPT["title"]))

    _as("u-1001")
    assert _review(c["id"], "live").json()["status"] == "live"
    _as("demo-credit")
    theirs = next(h for h in _ask("/api/prompts/search", PROMPT["title"])["hits"] if h["ref"] == ref)
    assert theirs["meta"] == "Contributed prompt · Approved"
    # Where an approved contribution lives is for its owners to confirm.
    assert theirs["href"] == ""


@pytest.mark.parametrize(
    "changes, audience",
    [
        ({"scope": "team"}, "team"),
        ({"scope": "dept"}, "department"),
        # High risk keeps it to the author's desk, whatever scope was chosen.
        ({"scope": "other", "safety": {"client_data": True, "mnpi": True, "feeds_control": False}}, "team"),
    ],
)
def test_approval_opens_it_only_to_its_audience(changes, audience):
    _as("demo-rm")
    c = _submit(**changes)
    assert c["audience"] == audience
    _as("u-1001")
    assert _review(c["id"], "live").status_code == 200
    # Another desk, and another department.
    _as("demo-credit")
    assert f"contribution:{c['id']}" not in _refs(_ask("/api/prompts/search", PROMPT["title"]))


def test_only_reviewers_decide_and_returned_work_leaves_search():
    _as("demo-rm")
    c = _submit()
    ref = f"contribution:{c['id']}"
    assert _review(c["id"], "live").status_code == 403

    _as("u-1001")
    assert _review(c["id"], "returned").json()["status"] == "returned"
    assert prompts_agent.agent.semantic.stored(ref) is None
    _as("demo-rm")
    assert ref not in _refs(_ask("/api/prompts/search", PROMPT["title"]))
    assert client.get("/api/contributions/mine").json()[0]["status"] == "returned"


def test_the_index_is_rebuilt_from_the_contributions_table():
    _as("demo-rm")
    c = _submit()
    ref = f"contribution:{c['id']}"
    prompts_agent.agent.remove(ref, "contribution")
    assert prompts_agent.agent.semantic.stored(ref) is None
    reindex()
    assert prompts_agent.agent.semantic.stored(ref)["owner"] == "demo-rm"


# ---------------------------------------------------------------------- hub


def test_the_home_assistant_answers_from_the_agents():
    _as("demo-rm")
    c = _submit()
    body = client.post("/api/ask", json={"q": "find a prompt for a leveraged deal teaser screening note"}).json()
    groups = {g["pillar"]: g for g in body["pillars"]}
    assert groups["prompts"]["retrieval"] == "hybrid"
    assert f"contribution:{c['id']}" in [h["ref"] for h in groups["prompts"]["hits"]]
