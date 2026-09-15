"""Event-driven progressive response streaming: what the page receives, and when."""

import json
import time

from fastapi.testclient import TestClient

from app.hub import llm, pillars, planner, synthesis
from app.main import app

client = TestClient(app)


def _events(q: str, **extra) -> list[dict]:
    response = client.post("/api/ask/stream", json={"q": q, "persona": "relationship_manager", **extra})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data:")]


def test_a_task_streams_understanding_the_plan_each_pillar_the_reply_then_the_answer():
    events = _events("Prepare for a client meeting")
    types = [e["type"] for e in events]
    assert types[0] == "accepted" and types[-1] == "complete"
    assert (
        types.index("task_understood")
        < types.index("plan_ready")
        < types.index("pillar_result")
        < types.index("response")
        < types.index("complete")
    )
    final = events[-1]["response"]
    assert final["kind"] == "task" and final["turn_id"]
    assert final["session_id"] == events[0]["session_id"]
    # Every pillar the plan named arrived on its own before the whole answer did.
    arrived = {e["group"]["pillar"] for e in events if e["type"] == "pillar_result"}
    assert arrived == set(final["plan"]["selected_pillars"])
    assert next(e for e in events if e["type"] == "toolkit")["recommended"] == final["recommended"]
    assert next(e for e in events if e["type"] == "response")["reply"] == final["reply"]


def test_each_pillar_arrives_the_moment_it_finishes(monkeypatch):
    def taking(seconds):
        def search(*args, **kwargs):
            time.sleep(seconds)
            return pillars.Run()

        return search

    monkeypatch.setattr(pillars, "marketplace", taking(0.5))
    monkeypatch.setattr(pillars, "prompts", taking(0.05))
    monkeypatch.setattr(pillars, "learning", taking(0.25))
    events = _events("Find an agent, a prompt and a course on covenant monitoring")
    assert [e["group"]["pillar"] for e in events if e["type"] == "pillar_result"] == [
        "prompts",
        "learning",
        "marketplace",
    ]


def test_the_reply_streams_in_pieces_with_the_client_put_back(monkeypatch):
    monkeypatch.setenv("CREDITWIZ_DISABLE_LLM", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(
        llm,
        "plan",
        lambda *args: llm.ModelPlan(small_talk=False,
            intents=["find", "learn"],
            objective="Get ready for the meeting",
            activity="meeting-prep",
            needs=[],
            sensitivity="client_confidential",
            sensitivity_reason="Names a client.",
            subqueries=[llm.PlannedQuery(pillar="prompts", query="client meeting brief", reformulated=True)],
        ),
    )

    def write(request, intents, job, items, on_delta=None):
        assert "Starbucks" not in request
        text = f"Start with {items[0][1]} before you see [CLIENT]."
        # Seven characters at a time, so "[CLIENT]" arrives split in two.
        for i in range(0, len(text), 7):
            on_delta(text[i : i + 7])
        return text

    monkeypatch.setattr(llm, "write", write)
    events = _events("Find a pitch prompt and a course to prepare for the Starbucks meeting")
    streamed = "".join(e["delta"] for e in events if e["type"] == "response_delta")
    assert streamed.endswith("before you see Starbucks.") and "[CLIENT]" not in streamed
    assert events[-1]["response"]["reply"] == streamed


def test_the_intents_arrive_while_the_model_plans_and_nothing_unvetted_is_shown(monkeypatch):
    monkeypatch.setenv("CREDITWIZ_DISABLE_LLM", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def slow_plan(*args):
        time.sleep(0.4)
        return llm.ModelPlan(small_talk=False, 
            intents=["find", "learn"],
            objective="",
            activity=None,
            needs=[],
            sensitivity="internal",
            sensitivity_reason="",
            subqueries=[llm.PlannedQuery(pillar="prompts", query="covenant monitoring", reformulated=False)],
        )

    monkeypatch.setattr(llm, "plan", slow_plan)
    monkeypatch.setattr(llm, "write", lambda *args, **kwargs: None)
    # The rules' reading of the intents streams at once, while the model plans.
    events = _events("Find a prompt and a course on covenant monitoring")
    assert events[1]["type"] == "task_understood" and events[1]["provisional"] is True
    # Nothing is searched until the model's plan says where.
    planned = next(i for i, e in enumerate(events) if e["type"] == "task_understood" and e["planned_by"] == "claude")
    assert not any(e["type"] in ("pillar_result", "toolkit") for e in events[:planned])
    assert not any(e.get("provisional") for e in events if e["type"] != "task_understood")
    assert any(
        h["title"] == "Covenant compliance monitor" for e in events if e["type"] == "pillar_result" for h in e["group"]["hits"]
    )
    # The final answer is the model's plan, not the first reading, and asks
    # the place for each of its two intents.
    assert events[-1]["response"]["plan"]["plan_source"] == "claude"
    assert events[-1]["response"]["plan"]["selected_pillars"] == ["prompts", "learning"]


def test_without_a_model_there_is_no_first_reading_to_replace():
    events = _events("Who can help with a credit request?")
    assert not any(e.get("provisional") for e in events)


def test_the_jobs_toolkit_arrives_only_after_the_agents_have_searched():
    events = _events("make my portfolio review faster")
    types = [e["type"] for e in events]
    assert "toolkit" in types and "pillar_result" in types
    assert types.index("toolkit") > max(i for i, t in enumerate(types) if t == "pillar_result")
    assert types.index("toolkit") < types.index("response")


def test_small_talk_completes_at_once_with_nothing_planned():
    events = _events("Hello!")
    assert [e["type"] for e in events] == ["accepted", "response", "complete"]
    assert events[-1]["response"]["kind"] == "greeting"


def test_the_question_never_travels_in_the_url():
    assert client.get("/api/ask/stream", params={"q": "Starbucks"}).status_code in (404, 405)
