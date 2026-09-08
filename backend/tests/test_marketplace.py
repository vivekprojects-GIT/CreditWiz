import os

import pytest
from fastapi.testclient import TestClient

os.environ["CREDITWIZ_DISABLE_LLM"] = "1"

from app.main import app  # noqa: E402
from app.marketplace import search  # noqa: E402
from app.marketplace.models import Agent  # noqa: E402
from app.marketplace.store import normalize_agent  # noqa: E402
from app.marketplace.store import store  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_var_dir(tmp_path, monkeypatch):
    from app.context import store as context_store
    from app.learning import progress as learning_progress

    monkeypatch.setattr(context_store, "_VAR_DIR", tmp_path)
    monkeypatch.setattr(learning_progress, "_VAR_DIR", tmp_path)


def test_agents_load_and_validate():
    agents = store.agents
    assert len(agents) == 10
    assert all(a.owner.email and a.access.how for a in agents)
    assert {a.id for a in agents} >= {"kyc-document-verifier", "contract-analyzer", "asset-locator"}


def test_home_builds_carousels_for_persona():
    body = client.get("/api/marketplace/home", params={"persona": "compliance_user"}).json()
    assert body["persona"] == "compliance_user"
    ids = [c["id"] for c in body["carousels"]]
    assert ids[0] == "recommended"
    recommended = [a["id"] for a in body["carousels"][0]["agents"]]
    assert recommended[0] in {"kyc-document-verifier", "kyc-risk-screening"}
    assert "code-review-assistant" not in recommended[:3]


def test_developer_persona_sees_code_review_first():
    body = client.get("/api/marketplace/home", params={"persona": "developer"}).json()
    recommended = [a["id"] for a in body["carousels"][0]["agents"]]
    assert recommended[0] == "code-review-assistant"


def test_nlp_search_understands_onboarding_documents():
    body = client.post(
        "/api/marketplace/search",
        json={"query": "I need an agent that can review customer onboarding documents", "persona": "compliance_user"},
    ).json()
    assert body["engine"] == "local"
    assert body["no_match"] is False
    top = [m["agent"]["id"] for m in body["results"]]
    assert top[0] in {"kyc-document-verifier", "onboarding-pack-assistant"}
    assert "Customer onboarding / KYC" in body["intent"]["concepts"]
    assert body["results"][0]["reasons"]


def test_nlp_search_paraphrase_without_keyword_overlap():
    body = client.post("/api/marketplace/search", json={"query": "someone owes us money, where are their assets"}).json()
    top = [m["agent"]["id"] for m in body["results"]]
    assert top[0] == "asset-locator"


def test_search_no_match_returns_next_steps():
    body = client.post("/api/marketplace/search", json={"query": "zebra origami"}).json()
    assert body["no_match"] is True
    assert body["results"] == []
    assert any(s["href"] == "/intake/new" for s in body["next_steps"])


def test_agent_detail_and_related():
    body = client.get("/api/marketplace/agents/kyc-document-verifier").json()
    assert body["owner"]["team"] == "Financial Crime Technology"
    related = client.get("/api/marketplace/agents/kyc-document-verifier/related").json()
    assert related and related[0]["id"] != "kyc-document-verifier"
    assert client.get("/api/marketplace/agents/nope").status_code == 404


def test_shared_context_layer_is_hub_wide_not_pillar_owned(tmp_path):
    """Every pillar writes the same shapes to one store."""
    m = client.post(
        "/api/context/events",
        json={"pillar": "marketplace", "type": "view", "subject_id": "contract-analyzer", "subject_type": "agent", "topics": ["Legal"]},
    ).json()
    assert m["ok"] and m["id"]
    l = client.post(
        "/api/context/events",
        json={"pillar": "learning", "type": "learning_view", "subject_id": "how-to-build-a-kyc-agent", "subject_type": "video", "topics": ["kyc", "Legal"]},
    ).json()
    assert l["ok"]

    summary = client.get("/api/context/summary").json()
    assert summary["total_events"] == 2
    assert {p["pillar"] for p in summary["by_pillar"]} == {"marketplace", "learning"}

    # one shared file, not one per pillar
    assert (tmp_path / "interactions.jsonl").exists()
    assert not list(tmp_path.glob("*marketplace*"))


def test_interests_aggregate_across_pillars():
    client.post("/api/context/events", json={"pillar": "learning", "type": "learning_view", "topics": ["kyc"]})
    client.post("/api/context/events", json={"pillar": "marketplace", "type": "search", "query": "kyc", "topics": ["kyc", "Compliance"]})
    client.post("/api/context/events", json={"pillar": "marketplace", "type": "launch", "topics": ["kyc"]})
    interests = client.get("/api/context/interests").json()
    top = interests[0]
    assert top["topic"] == "kyc"
    assert top["weight"] == 1.0
    assert sorted(top["pillars"]) == ["learning", "marketplace"]


def test_user_context_joins_profile_persona_and_footprints():
    client.post("/api/context/events", json={"pillar": "learning", "type": "learning_view", "topics": ["kyc"]})
    ctx = client.get("/api/context/me").json()
    assert ctx["persona"] == "compliance_user"
    assert ctx["job_title"] == "Compliance Analyst"
    assert ctx["pillars_seen"] == ["learning"]
    assert ctx["interests"][0]["topic"] == "kyc"


def test_feedback_is_hub_wide(tmp_path):
    client.post(
        "/api/context/feedback",
        json={"pillar": "learning", "context": "video", "helpful": False, "subject_id": "v1", "missing": "Need a payroll video"},
    )
    client.post("/api/context/feedback", json={"pillar": "marketplace", "context": "search", "helpful": True})
    s = client.get("/api/context/summary").json()
    assert s["total_feedback"] == 2 and s["helpful"] == 1 and s["not_helpful"] == 1
    assert s["recent_missing"] == ["Need a payroll video"]
    assert (tmp_path / "feedback.jsonl").exists()


def test_deprecated_marketplace_endpoints_still_write_to_shared_store():
    client.post("/api/marketplace/events", json={"type": "agent_view", "agent_id": "contract-analyzer"})
    s = client.get("/api/context/summary").json()
    assert s["by_pillar"][0]["pillar"] == "marketplace"


def test_metadata_template_lists_required_fields():
    tpl = client.get("/api/marketplace/metadata-template").json()
    for field in ("id", "name", "business_domains", "use_cases", "capabilities", "personas", "owner", "status",
                  "platform", "tools_services", "models", "access", "documentation_url", "architecture_url",
                  "created_at", "updated_at"):
        assert field in tpl


def test_local_intent_lexicon():
    intent = search.local_intent("screen a new customer against sanctions lists")
    assert "AML screening" in intent.concepts
    assert "Compliance" in intent.domains


SIMPLE_INTAKE_RECORD = {
    "agentId": "agent-001",
    "name": "KYC Verification Agent",
    "description": "Helps validate customer identity and KYC documents.",
    "domain": "Compliance",
    "useCases": ["Customer onboarding", "Identity verification"],
    "capabilities": ["Document validation", "Identity verification", "Compliance checks"],
    "personas": ["Compliance User", "Business User"],
    "platform": "AWS",
    "owner": "KYC AI Team",
    "status": "Production",
    "tools": [],
    "models": [],
    "documentationUrl": "",
    "architectureUrl": "",
    "launchUrl": "",
    "createdDate": "",
    "updatedDate": "",
}


def test_simple_intake_format_normalises_to_canonical_model():
    agent = Agent.model_validate(normalize_agent(SIMPLE_INTAKE_RECORD))
    assert agent.id == "agent-001"
    assert agent.business_domains == ["Compliance"]
    assert agent.personas == ["compliance_user", "business_user"]
    assert agent.owner.team == "KYC AI Team"
    assert agent.status == "production"
    assert agent.category == "Compliance & Risk"
    assert agent.tagline.startswith("Helps validate")
    assert agent.use_cases == ["Customer onboarding", "Identity verification"]


def test_search_results_explain_why():
    body = client.post(
        "/api/marketplace/search",
        json={"query": "I need something for validating customer documents during onboarding"},
    ).json()
    top = body["results"][0]
    assert top["agent"]["id"] in {"kyc-document-verifier", "onboarding-pack-assistant"}
    assert top["why"].startswith("This agent")
    assert "onboarding" in top["why"].lower() or "document" in top["why"].lower()


def test_event_types_follow_agreed_names():
    for t in ("search", "agent_view", "agent_click", "agent_launch", "documentation_click", "request_access", "feedback_positive", "feedback_negative"):
        assert client.post("/api/marketplace/events", json={"type": t}).status_code == 200
    assert client.post("/api/marketplace/events", json={"type": "view_agent"}).status_code == 422


def test_agent_docs_and_architecture_pages():
    docs = client.get("/api/marketplace/agents/kyc-document-verifier/docs").json()
    assert docs["title"].startswith("KYC Document Verifier")
    assert "## Getting started" in docs["markdown"]
    arch = client.get("/api/marketplace/agents/kyc-document-verifier/architecture").json()
    assert arch["title"] == "Document agent pattern"
    assert "How it works" in arch["markdown"]
    assert client.get("/api/marketplace/agents/nope/docs").status_code == 404


def test_learning_for_agent_is_persona_ordered():
    recs = client.get("/api/learning/for-agent/kyc-document-verifier", params={"persona": "compliance_user"}).json()
    ids = [i["id"] for i in recs]
    assert "kyc-verifier-walkthrough" in ids and len(ids) <= 3
    assert recs[0]["id"] == "kyc-verifier-walkthrough"          # domain primer first for compliance
    dev = [i["id"] for i in client.get("/api/learning/for-agent/kyc-document-verifier", params={"persona": "developer"}).json()]
    assert dev[0] == "how-to-build-a-kyc-agent"                 # builder content first for a developer


def test_learning_items_span_many_content_types():
    items = client.get("/api/learning/items").json()
    types = {i["type"] for i in items}
    assert {"video", "quick-reference", "best-practice", "documentation", "guide", "course", "confluence"} <= types
    assert len(items) >= 20
    assert client.get("/api/learning/items", params={"type": "quick-reference"}).json()
    assert client.get("/api/learning/items/nope").status_code == 404
    detail = client.get("/api/learning/items/kyc-verifier-walkthrough").json()
    assert detail["path_title"] and "kyc-document-verifier" in detail["related_agent_names"]


def test_learning_home_sections_are_role_based():
    body = client.get("/api/learning", params={"persona": "compliance_user"}).json()
    ids = [s["id"] for s in body["sections"]]
    assert ids[0] == "required"                                  # mandatory first
    assert {"role", "best-practice", "docs", "quick-reference"} <= set(ids)
    assert all(i["required"] for i in body["sections"][0]["items"])
    assert body["persona_label"] == "Compliance user"


def test_progress_tracks_started_and_completed():
    started = client.post("/api/learning/progress",
                          json={"item_id": "kyc-document-checklist", "status": "in_progress", "progress": 40}).json()
    assert started["status"] == "in_progress" and started["progress"] == 40

    again = client.post("/api/learning/progress",
                        json={"item_id": "kyc-document-checklist", "status": "in_progress", "progress": 10}).json()
    assert again["progress"] == 40                               # progress never regresses

    done = client.post("/api/learning/progress", json={"item_id": "kyc-document-checklist", "status": "completed"}).json()
    assert done["status"] == "completed" and done["progress"] == 100

    summary = client.get("/api/context/summary").json()           # completion is also a hub footprint
    assert any(p["pillar"] == "learning" and p["types"].get("learning_complete") for p in summary["by_pillar"])
    assert client.post("/api/learning/progress", json={"item_id": "nope", "status": "completed"}).status_code == 404


def test_my_learning_reports_progress_and_coverage_not_proficiency():
    client.post("/api/learning/progress", json={"item_id": "kyc-verifier-walkthrough", "status": "completed"})
    client.post("/api/learning/progress", json={"item_id": "sanctions-screening-basics", "status": "in_progress", "progress": 65})
    me = client.get("/api/learning/my-learning").json()
    assert me["completed"] >= 1 and me["in_progress"] >= 1
    assert me["required_total"] >= me["required_completed"]

    kyc = next(c for c in me["coverage"] if c["topic"] == "KYC")
    assert kyc["completed"] <= kyc["total"]                       # factual counts, never a percentage

    assert "agreed enterprise measure of proficiency" in me["proficiency_note"]
    assert not any("proficiency" in k.lower() and k != "proficiency_note" for k in me)


def test_progress_is_sqlite_and_survives_reads(tmp_path):
    """Progress is mutable state, so it lives in SQLite rather than a rewritten JSON file."""
    import sqlite3

    client.post("/api/learning/progress", json={"item_id": "prompt-patterns-one-pager", "status": "in_progress", "progress": 30})
    db = tmp_path / "learning.db"
    assert db.exists()

    rows = sqlite3.connect(db).execute(
        "SELECT user_id, item_id, status, progress FROM learning_progress"
    ).fetchall()
    assert ("u-1001", "prompt-patterns-one-pager", "in_progress", 30) in rows

    # concurrent-safe upsert: same row, not a duplicate
    client.post("/api/learning/progress", json={"item_id": "prompt-patterns-one-pager", "status": "completed"})
    rows = sqlite3.connect(db).execute("SELECT status, progress FROM learning_progress").fetchall()
    assert len(rows) == 1 and rows[0] == ("completed", 100)
