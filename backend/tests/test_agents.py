"""The Learning agent: the retrieval every pillar agent runs, and the home assistant answering from it."""

import pytest
from fastapi.testclient import TestClient

from app import database
from app.learning import agent as learning_agent
from app.learning.store import store as catalog_store
from app.main import app

client = TestClient(app)


def _as(user_id: str) -> None:
    client.cookies.clear()
    assert client.post("/api/auth/demo", json={"user_id": user_id}).status_code == 200


def _ask(path: str, query: str) -> dict:
    response = client.post(path, json={"query": query})
    assert response.status_code == 200, response.text
    return response.json()


def _refs(answer: dict) -> list[str]:
    return [h["ref"] for h in answer["hits"]]


# ---------------------------------------------------------------- retrieval


def test_the_learning_agent_finds_courses_by_what_they_teach():
    answer = _ask("/api/learning/search", "learn prompt engineering")
    assert answer["retrieval"] == "hybrid"
    assert "Prompt patterns for analysts" in [h["title"] for h in answer["hits"]]
    assert all(r.startswith("learning:") for r in _refs(answer))
    best = answer["hits"][0]
    assert best["similarity"] is not None and best["keyword"] is not None


@pytest.mark.parametrize("nonsense", ["zebra origami", "best pizza near me", "tell me a joke"])
def test_nonsense_finds_nothing(nonsense):
    assert _ask("/api/learning/search", nonsense)["hits"] == []


def test_an_agent_retrieves_only_from_what_it_is_handed():
    _, items = catalog_store.catalog
    wanted = items[0]
    pool = [i for i in items if i.id != wanted.id]
    _, hits = learning_agent.find([wanted.title], pool, persona_id="")
    assert f"learning:{wanted.id}" not in [h.ref for h in hits]


def test_a_client_name_reaches_no_index_and_no_log():
    _as("demo-rm")
    answer = _ask("/api/learning/search", "prompt engineering course for Acme Holdings")
    assert "Acme" not in answer["query"]
    with database.connect() as conn:
        logged = [r["payload"] for r in conn.execute("SELECT payload FROM events")]
    assert logged and not any("Acme" in p for p in logged)


# ---------------------------------------------------------------------- hub


def test_the_home_assistant_answers_from_the_agents():
    _as("demo-rm")
    body = client.post("/api/ask", json={"q": "find a course on prompt engineering"}).json()
    groups = {g["pillar"]: g for g in body["pillars"]}
    assert set(groups) <= {"marketplace", "learning"}
    assert groups["learning"]["retrieval"] == "hybrid"
    assert "Prompt patterns for analysts" in [h["title"] for h in groups["learning"]["hits"]]
