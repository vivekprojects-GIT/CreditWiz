"""The prompt library, the courses joined to Learning, and Create."""

from fastapi.testclient import TestClient

from app.main import app
from app.prompts.draft import constraints_of
from app.prompts.store import store

client = TestClient(app)


def _as(user_id: str) -> None:
    client.cookies.clear()
    assert client.post("/api/auth/demo", json={"user_id": user_id}).status_code == 200


def _prompt(**changes) -> dict:
    body = {
        "kind": "prompt",
        "title": "Deal screening summary",
        "description": "Summarises a teaser into a screening note.",
        "category": "Corporate Banking",
        "tags": ["Screening", "Origination"],
        "scope": "team",
        "body": "ROLE: You are a coverage banker at MUFG.\n\nCONSTRAINTS\n- Never estimate.",
        "inputs": ["Deal teaser"],
        "hours_saved": 3,
        "safety": {"client_data": True, "mnpi": False, "feeds_control": False},
        "guidelines": ["Check every figure against the teaser."],
        "tested": True,
        "learned_from": ["p1"],
    }
    return {**body, **changes}


# ------------------------------------------------------------------ library


def test_the_library_holds_sixty_validated_prompts_from_three_desks():
    body = client.get("/api/prompts", params={"desk": "all"}).json()
    assert body["total"] == 60
    assert {d["id"] for d in body["desks"]} == {"relationship-manager", "credit-analyst", "risk-analyst"}
    assert all(p["validated"] and p["source_kind"] == "sample" for p in body["prompts"])


def test_a_relationship_manager_sees_their_own_desk_first():
    _as("demo-rm")
    mine = client.get("/api/prompts").json()
    assert mine["desk"]["id"] == "relationship-manager" and mine["showing"] == "relationship-manager"
    assert mine["total"] == 20
    others = client.get("/api/prompts", params={"desk": "risk-analyst"}).json()
    assert {p["relation"] for p in others["prompts"]} == {"other"}


def test_a_credit_analyst_has_their_own_desk_and_the_risk_analyst_persona():
    _as("demo-credit")
    assert client.get("/api/me").json()["persona"]["id"] == "risk_analyst"
    assert client.get("/api/prompts").json()["desk"]["id"] == "credit-analyst"


def test_search_finds_a_prompt_by_the_words_of_its_job():
    body = client.get("/api/prompts", params={"desk": "all", "q": "pitch deck"}).json()
    assert body["prompts"][0]["title"] == "Corporate pitch structurer"


def test_a_prompt_opens_in_full():
    p = client.get("/api/prompts/p1").json()
    assert p["inputs"] and p["guidelines"] and p["sample_output"] and p["reviews"]
    assert "CONSTRAINTS" in p["body"] and p["risk"] == "Low"
    assert client.get("/api/prompts/nope").status_code == 404


def test_saving_a_prompt_puts_it_in_my_library():
    assert client.put("/api/prompts/p2/saved").json() == {"saved": True}
    saved = client.get("/api/prompts", params={"desk": "all", "sort": "saved"}).json()["prompts"]
    assert [p["id"] for p in saved] == ["p2"]
    assert client.delete("/api/prompts/p2/saved").json() == {"saved": False}
    assert client.get("/api/prompts", params={"desk": "all", "sort": "saved"}).json()["prompts"] == []


def test_four_templates_start_a_new_prompt():
    names = [t["name"] for t in client.get("/api/prompts/templates").json()]
    assert names == ["Analysis and synthesis", "Extraction and flagging", "Scenario and stress", "Client-facing draft"]


def test_the_top_bar_search_finds_prompts():
    results = client.get("/api/search", params={"q": "covenant"}).json()["results"]
    assert any(r["kind"] == "prompt" and r["href"].startswith("/library/prompts/") for r in results)


# ------------------------------------------------------------------ courses


def test_catalogue_courses_join_learning_with_lessons_and_outcomes():
    items = client.get("/api/learning/items", params={"q": "IFRS 9"}).json()
    course = next(i for i in items if i["id"] == "ifrs-9-expected-credit-loss-in-practice")
    assert course["lessons"] and course["outcomes"]
    assert course["source"] == "LinkedIn Learning" and course["instructor"] == "Marilyn Hayes"


def test_a_retired_course_is_not_offered():
    ids = {i["id"] for i in client.get("/api/learning/items").json()}
    assert "excel-modelling-for-bankers-2023-edition" not in ids
    assert "prompting-the-mufg-secure-llm" in ids


# ------------------------------------------------------------------- create


def test_a_submitted_prompt_waits_for_review_with_the_risk_its_declaration_implies():
    response = client.post("/api/contributions", json=_prompt())
    assert response.status_code == 201
    c = response.json()
    assert c["status"] == "in_review" and c["risk"] == "Medium"
    assert "Data Privacy Office" in c["review"]
    assert [m["id"] for m in client.get("/api/contributions/mine").json()] == [c["id"]]


def test_mnpi_or_an_output_that_feeds_a_control_means_high_risk():
    for safety in ({"client_data": False, "mnpi": True, "feeds_control": False},
                   {"client_data": False, "mnpi": False, "feeds_control": True}):
        assert client.post("/api/contributions", json=_prompt(safety=safety)).json()["risk"] == "High"
    none = {"client_data": False, "mnpi": False, "feeds_control": False}
    assert client.post("/api/contributions", json=_prompt(safety=none)).json()["risk"] == "Low"


def test_an_untested_prompt_is_not_accepted():
    assert client.post("/api/contributions", json=_prompt(tested=False)).status_code == 422


def test_unknown_categories_and_sources_are_refused():
    assert client.post("/api/contributions", json=_prompt(category="Astrology")).status_code == 422
    assert client.post("/api/contributions", json=_prompt(learned_from=["zzz"])).status_code == 422


def test_an_agent_proposal_chains_validated_prompts():
    ok = client.post(
        "/api/contributions", json={"kind": "agent", "title": "Credit application assistant", "chain": ["p5", "p6"]}
    )
    assert ok.status_code == 201 and "Model Risk" in ok.json()["review"]
    assert client.post("/api/contributions", json={"kind": "agent", "title": "Empty", "chain": []}).status_code == 422
    assert client.post("/api/contributions", json={"kind": "agent", "title": "Bad", "chain": ["zzz"]}).status_code == 422


def test_a_video_is_submitted_by_file_name_only():
    c = client.post(
        "/api/contributions",
        json={"kind": "video", "title": "Structuring an RFP response", "recording": "Walkthrough_v1.mp4"},
    ).json()
    assert c["kind"] == "video" and c["status"] == "in_review" and c["risk"] is None


def test_contributions_are_private_to_their_author():
    client.post("/api/contributions", json=_prompt())
    _as("demo-rm")
    assert client.get("/api/contributions/mine").json() == []


def test_a_draft_inherits_the_constraints_of_the_prompts_it_learned_from():
    d = client.post(
        "/api/prompts/draft", json={"goal": "write a prompt that summarises an annual review pack for Starbucks"}
    ).json()
    assert "Starbucks" not in d["body"] and "Starbucks" not in d["goal"]
    assert d["goal"] == "summarises an annual review pack for [CLIENT]"
    inherited = {c for s in d["learned_from"] for c in constraints_of(store.prompt(s["id"]))}
    drafted = {line[2:] for line in d["body"].split("CONSTRAINTS", 1)[1].splitlines() if line.startswith("- ")}
    assert drafted and drafted <= inherited
