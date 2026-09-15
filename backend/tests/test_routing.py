"""Each request asks only the places its intents call for, and the job's
toolkit brings only the kind of thing asked for. Only a request with more
than one intent asks more than one kind of place."""

import pytest
from fastapi.testclient import TestClient

from app.hub import llm
from app.main import app

client = TestClient(app)
RM = {"persona": "relationship_manager"}
EVERY_PILLAR = ("prompts", "marketplace", "learning", "community")


def _ask(q: str) -> dict:
    response = client.post("/api/ask", json={"q": q, **RM})
    assert response.status_code == 200, response.text
    return response.json()


def _kinds(body: dict) -> set[str]:
    return {c["kind"] for c in body["recommended"]}


@pytest.mark.parametrize(
    "q, pillars, searched",
    [
        ("find me a compliance agent", ["marketplace"], "compliance"),
        ("I need a prompt for a credit memo", ["prompts"], "credit memo"),
        # "prompt" is the topic here, not the kind of thing asked for.
        ("course on prompt engineering", ["learning"], "prompt engineering"),
        ("who is the expert on KYC", ["community"], "KYC"),
        # The words that decided the intent are not what it is about.
        ("help me get better at credit analysis", ["learning"], "credit analysis"),
        ("any tutorials on VaR", ["learning"], "VaR"),
    ],
)
def test_one_intent_asks_one_kind_of_place_for_what_it_is_about(q, pillars, searched):
    body = _ask(q)
    assert body["plan"]["selected_pillars"] == pillars
    assert [s["query"] for s in body["plan"]["subqueries"]] == [searched]
    assert [g["pillar"] for g in body["pillars"]] == pillars


def test_finding_without_naming_a_kind_asks_both_catalogues_for_the_subject():
    body = _ask("make my portfolio review faster")
    assert body["task"]["intents"] == ["improve"]
    assert body["plan"]["selected_pillars"] == ["prompts", "marketplace"]
    assert {s["query"] for s in body["plan"]["subqueries"]} == {"portfolio review"}


def test_a_cue_that_is_the_subject_stays_in_the_search():
    body = _ask("who knows our policy on gifts")
    assert "policy" in body["plan"]["subqueries"][0]["query"]


def test_a_new_request_does_not_inherit_the_last_job():
    body = client.post(
        "/api/ask", json={"q": "find me a compliance agent", **RM, "journey": "credit-request"}
    ).json()
    assert body["task"]["activity"] is None and body["task"]["carried_over"] is False
    assert body["recommended"] == []
    assert body["plan"]["selected_pillars"] == ["marketplace"]
    # A follow-up that points back at it stays on it.
    body = client.post("/api/ask", json={"q": "and which agent does this faster?", **RM, "journey": "credit-request"}).json()
    assert body["task"]["activity"]["id"] == "credit-request" and body["task"]["carried_over"] is True


def test_the_job_toolkit_brings_only_the_kind_asked_for():
    prompt = _ask("I need a prompt for a credit memo")
    assert prompt["task"]["activity"] is not None
    assert _kinds(prompt) == {"prompt"}
    expert = _ask("who is the expert on KYC")
    assert expert["task"]["activity"] is not None
    assert expert["recommended"] and _kinds(expert) <= {"expert", "community"}


@pytest.fixture
def model(monkeypatch):
    """A planner that, like a real one might, proposes every pillar."""
    monkeypatch.setenv("CREDITWIZ_DISABLE_LLM", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "write", lambda *args, **kwargs: None)

    def plans(intents):
        monkeypatch.setattr(
            llm,
            "plan",
            lambda *args: llm.ModelPlan(
                small_talk=False,
                intents=intents,
                objective="Screen for sanctions",
                activity=None,
                needs=[],
                sensitivity="internal",
                sensitivity_reason="",
                subqueries=[
                    llm.PlannedQuery(pillar=p, query="sanctions screening", reformulated=False) for p in EVERY_PILLAR
                ],
            ),
        )

    return plans


def test_asking_for_a_kind_of_thing_outright_is_an_intent_of_its_own():
    body = _ask("I want a prompt for covenant monitoring and someone who knows covenants")
    assert set(body["task"]["intents"]) == {"ask", "find"}
    assert set(body["plan"]["selected_pillars"]) == {"community", "prompts"}


def test_asking_for_an_agent_decides_the_plan_without_a_model():
    body = _ask("is there an agent for sanctions screening")
    assert body["task"]["intents"] == ["find"]
    assert body["task"]["intent_cue"] == "an agent"
    assert body["plan"]["selected_pillars"] == ["marketplace"]
    assert _kinds(body) <= {"agent"}


def test_getting_better_at_something_is_learning_it():
    body = _ask("help me get better at credit analysis")
    assert body["task"]["intents"] == ["learn"]
    assert body["plan"]["selected_pillars"] == ["learning"]


def test_the_model_cannot_spread_one_intent_across_every_pillar(model):
    model(["find"])
    body = _ask("compliance agent")
    assert body["plan"]["plan_source"] == "claude"
    assert body["plan"]["selected_pillars"] == ["marketplace"]
    assert [g["pillar"] for g in body["pillars"]] == ["marketplace"]
    assert _kinds(body) <= {"agent"}
    assert "Only the places its intents call for were searched." in body["plan"]["plan_reason"]


def test_a_request_with_two_intents_asks_the_place_for_each(model):
    model(["find", "learn"])
    body = _ask("find an agent and a course for sanctions screening")
    assert body["plan"]["selected_pillars"] == ["marketplace", "learning"]
    assert _kinds(body) <= {"agent", "learning"}
    assert {s["query"] for s in body["plan"]["subqueries"]} == {"sanctions screening"}
