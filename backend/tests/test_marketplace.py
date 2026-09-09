import os

from fastapi.testclient import TestClient

os.environ["CREDITWIZ_DISABLE_LLM"] = "1"

from app.main import app  # noqa: E402
from app.marketplace import search  # noqa: E402
from app.marketplace.models import Agent  # noqa: E402
from app.marketplace.store import normalize_agent  # noqa: E402
from app.marketplace.store import store  # noqa: E402

client = TestClient(app)


def test_agents_load_and_validate():
    agents = store.agents
    assert len(agents) == 10
    assert all(a.owner.email and a.access.how for a in agents)
    assert {a.id for a in agents} >= {
        "kyc-document-verifier",
        "contract-analyzer",
        "asset-locator",
    }


def test_home_builds_carousels_for_persona():
    body = client.get(
        "/api/marketplace/home", params={"persona": "compliance_user"}
    ).json()
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
        json={
            "query": "I need an agent that can review customer onboarding documents",
            "persona": "compliance_user",
        },
    ).json()
    assert body["engine"] == "local"
    assert body["no_match"] is False
    top = [m["agent"]["id"] for m in body["results"]]
    assert top[0] in {"kyc-document-verifier", "onboarding-pack-assistant"}
    assert "Customer onboarding / KYC" in body["intent"]["concepts"]
    assert body["results"][0]["reasons"]


def test_nlp_search_paraphrase_without_keyword_overlap():
    body = client.post(
        "/api/marketplace/search",
        json={"query": "someone owes us money, where are their assets"},
    ).json()
    top = [m["agent"]["id"] for m in body["results"]]
    assert top[0] == "asset-locator"


def test_search_no_match_returns_next_steps():
    body = client.post(
        "/api/marketplace/search", json={"query": "zebra origami"}
    ).json()
    assert body["no_match"] is True
    assert body["results"] == []
    assert any(s["href"] == "/learning/catalog" for s in body["next_steps"])


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
        json={
            "pillar": "marketplace",
            "type": "view",
            "subject_id": "contract-analyzer",
            "subject_type": "agent",
            "topics": ["Legal"],
        },
    ).json()
    assert m["ok"] and m["id"]
    l = client.post(
        "/api/context/events",
        json={
            "pillar": "learning",
            "type": "learning_view",
            "subject_id": "how-to-build-a-kyc-agent",
            "subject_type": "video",
            "topics": ["kyc", "Legal"],
        },
    ).json()
    assert l["ok"]

    summary = client.get("/api/context/summary").json()
    assert summary["total_events"] == 2
    assert {p["pillar"] for p in summary["by_pillar"]} == {"marketplace", "learning"}

    # one shared file, not one per pillar
    assert (tmp_path / "hub.db").exists()
    assert not list(tmp_path.glob("*marketplace*"))


def test_interests_aggregate_across_pillars():
    client.post(
        "/api/context/events",
        json={"pillar": "learning", "type": "learning_view", "topics": ["kyc"]},
    )
    client.post(
        "/api/context/events",
        json={
            "pillar": "marketplace",
            "type": "search",
            "query": "kyc",
            "topics": ["kyc", "Compliance"],
        },
    )
    client.post(
        "/api/context/events",
        json={"pillar": "marketplace", "type": "launch", "topics": ["kyc"]},
    )
    interests = client.get("/api/context/interests").json()
    top = interests[0]
    assert top["topic"] == "kyc"
    assert top["weight"] == 1.0
    assert sorted(top["pillars"]) == ["learning", "marketplace"]


def test_user_context_joins_profile_persona_and_footprints():
    client.post(
        "/api/context/events",
        json={"pillar": "learning", "type": "learning_view", "topics": ["kyc"]},
    )
    ctx = client.get("/api/context/me").json()
    assert ctx["persona"] == "compliance_user"
    assert ctx["job_title"] == "Compliance Analyst"
    assert ctx["pillars_seen"] == ["learning"]
    assert ctx["interests"][0]["topic"] == "kyc"


def test_feedback_is_hub_wide(tmp_path):
    client.post(
        "/api/context/feedback",
        json={
            "pillar": "learning",
            "context": "video",
            "helpful": False,
            "subject_id": "v1",
            "missing": "Need a payroll video",
        },
    )
    client.post(
        "/api/context/feedback",
        json={"pillar": "marketplace", "context": "search", "helpful": True},
    )
    s = client.get("/api/context/summary").json()
    assert s["total_feedback"] == 2 and s["helpful"] == 1 and s["not_helpful"] == 1
    assert s["recent_missing"] == ["Need a payroll video"]
    assert (tmp_path / "hub.db").exists()


def test_deprecated_marketplace_endpoints_still_write_to_shared_store():
    client.post(
        "/api/marketplace/events",
        json={"type": "agent_view", "agent_id": "contract-analyzer"},
    )
    s = client.get("/api/context/summary").json()
    assert s["by_pillar"][0]["pillar"] == "marketplace"


def test_metadata_template_lists_required_fields():
    tpl = client.get("/api/marketplace/metadata-template").json()
    for field in (
        "id",
        "name",
        "business_domains",
        "use_cases",
        "capabilities",
        "personas",
        "owner",
        "status",
        "platform",
        "tools_services",
        "models",
        "access",
        "documentation_url",
        "architecture_url",
        "created_at",
        "updated_at",
    ):
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
    "capabilities": [
        "Document validation",
        "Identity verification",
        "Compliance checks",
    ],
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
        json={
            "query": "I need something for validating customer documents during onboarding"
        },
    ).json()
    top = body["results"][0]
    assert top["agent"]["id"] in {"kyc-document-verifier", "onboarding-pack-assistant"}
    assert top["why"].startswith("This agent")
    assert "onboarding" in top["why"].lower() or "document" in top["why"].lower()


def test_event_types_follow_agreed_names():
    for t in (
        "search",
        "agent_view",
        "agent_click",
        "agent_launch",
        "documentation_click",
        "request_access",
        "feedback_positive",
        "feedback_negative",
    ):
        assert (
            client.post("/api/marketplace/events", json={"type": t}).status_code == 200
        )
    assert (
        client.post("/api/marketplace/events", json={"type": "view_agent"}).status_code
        == 422
    )


def test_agent_docs_and_architecture_pages():
    docs = client.get("/api/marketplace/agents/kyc-document-verifier/docs").json()
    assert docs["title"].startswith("KYC Document Verifier")
    assert "## Getting started" in docs["markdown"]
    arch = client.get(
        "/api/marketplace/agents/kyc-document-verifier/architecture"
    ).json()
    assert arch["title"] == "Document agent pattern"
    assert "How it works" in arch["markdown"]
    assert client.get("/api/marketplace/agents/nope/docs").status_code == 404


def test_learning_for_agent_is_persona_ordered():
    recs = client.get(
        "/api/learning/for-agent/kyc-document-verifier",
        params={"persona": "compliance_user"},
    ).json()
    ids = [i["id"] for i in recs]
    assert "kyc-verifier-walkthrough" in ids and len(ids) <= 3
    assert (
        recs[0]["id"] == "kyc-verifier-walkthrough"
    )  # domain primer first for compliance
    dev = [
        i["id"]
        for i in client.get(
            "/api/learning/for-agent/kyc-document-verifier",
            params={"persona": "developer"},
        ).json()
    ]
    assert dev[0] == "how-to-build-a-kyc-agent"  # builder content first for a developer


def test_learning_items_span_many_content_types():
    items = client.get("/api/learning/items").json()
    types = {i["type"] for i in items}
    assert {
        "video",
        "quick-reference",
        "best-practice",
        "documentation",
        "guide",
        "course",
        "confluence",
    } <= types
    assert len(items) >= 20
    assert client.get("/api/learning/items", params={"type": "quick-reference"}).json()
    assert client.get("/api/learning/items/nope").status_code == 404
    detail = client.get("/api/learning/items/kyc-verifier-walkthrough").json()
    assert (
        detail["path_title"]
        and "kyc-document-verifier" in detail["related_agent_names"]
    )


def test_learning_home_sections_are_role_based():
    body = client.get("/api/learning", params={"persona": "compliance_user"}).json()
    ids = [s["id"] for s in body["sections"]]
    assert ids[0] == "required"  # mandatory first
    assert {"role", "best-practice", "docs", "quick-reference"} <= set(ids)
    assert all(i["required"] for i in body["sections"][0]["items"])
    assert body["persona_label"] == "Compliance user"


def test_progress_tracks_started_and_completed():
    started = client.post(
        "/api/learning/progress",
        json={
            "item_id": "kyc-document-checklist",
            "status": "in_progress",
            "progress": 40,
        },
    ).json()
    assert started["status"] == "in_progress" and started["progress"] == 40

    again = client.post(
        "/api/learning/progress",
        json={
            "item_id": "kyc-document-checklist",
            "status": "in_progress",
            "progress": 10,
        },
    ).json()
    assert again["progress"] == 40  # progress never regresses

    done = client.post(
        "/api/learning/progress",
        json={"item_id": "kyc-document-checklist", "status": "completed"},
    ).json()
    assert done["status"] == "completed" and done["progress"] == 100

    summary = client.get(
        "/api/context/summary"
    ).json()  # completion is also a hub footprint
    assert any(
        p["pillar"] == "learning" and p["types"].get("learning_complete")
        for p in summary["by_pillar"]
    )
    assert (
        client.post(
            "/api/learning/progress", json={"item_id": "nope", "status": "completed"}
        ).status_code
        == 404
    )


def test_my_learning_reports_progress_and_coverage_not_proficiency():
    client.post(
        "/api/learning/progress",
        json={"item_id": "kyc-verifier-walkthrough", "status": "completed"},
    )
    client.post(
        "/api/learning/progress",
        json={
            "item_id": "sanctions-screening-basics",
            "status": "in_progress",
            "progress": 65,
        },
    )
    me = client.get("/api/learning/my-learning").json()
    assert me["completed"] >= 1 and me["in_progress"] >= 1
    assert me["required_total"] >= me["required_completed"]

    kyc = next(c for c in me["coverage"] if c["topic"] == "KYC")
    assert kyc["completed"] <= kyc["total"]  # factual counts, never a percentage

    assert "agreed enterprise measure of proficiency" in me["proficiency_note"]
    assert not any("proficiency" in k.lower() and k != "proficiency_note" for k in me)


def test_rating_requires_the_learner_to_have_opened_the_item():
    """A rating from someone who never opened the content is not a signal."""
    assert (
        client.post(
            "/api/learning/ratings",
            json={"item_id": "kyc-verifier-walkthrough", "stars": 5},
        ).status_code
        == 409
    )
    client.post(
        "/api/learning/progress",
        json={"item_id": "kyc-verifier-walkthrough", "status": "in_progress"},
    )
    body = client.post(
        "/api/learning/ratings",
        json={"item_id": "kyc-verifier-walkthrough", "stars": 5},
    ).json()
    assert body["my_rating"] == 5 and body["rating_count"] == 1


def test_average_is_withheld_until_enough_ratings_but_weighted_value_exists():
    """One 5-star vote must not be published as "5.0"."""
    from app.learning import ratings

    client.post(
        "/api/learning/progress",
        json={"item_id": "kyc-verifier-walkthrough", "status": "in_progress"},
    )
    body = client.post(
        "/api/learning/ratings",
        json={"item_id": "kyc-verifier-walkthrough", "stars": 5},
    ).json()
    assert body["rating_count"] == 1 < ratings.MIN_SHOWN
    assert body["rating_average"] is None
    # Shrinkage pulls a lone 5 back toward the catalogue, so it cannot win a sort.
    assert body["rating_weighted"] < 5.0


def test_rating_again_replaces_rather_than_accumulates():
    client.post(
        "/api/learning/progress",
        json={"item_id": "kyc-verifier-walkthrough", "status": "in_progress"},
    )
    for stars in (2, 4):
        body = client.post(
            "/api/learning/ratings",
            json={"item_id": "kyc-verifier-walkthrough", "stars": stars},
        ).json()
    assert body["my_rating"] == 4 and body["rating_count"] == 1

    cleared = client.post(
        "/api/learning/ratings",
        json={"item_id": "kyc-verifier-walkthrough", "stars": None},
    ).json()
    assert cleared["my_rating"] is None and cleared["rating_count"] == 0


def test_average_appears_once_the_item_clears_the_threshold():
    """Three learners, three different scores: the mean becomes publishable."""
    from app.learning import ratings

    item = "kyc-verifier-walkthrough"
    for user, stars in (("u-1001", 5), ("demo-compliance", 4), ("demo-operations", 3)):
        assert client.post("/api/auth/demo", json={"user_id": user}).status_code == 200
        client.post("/api/learning/progress", json={"item_id": item, "status": "in_progress"})
        body = client.post(
            "/api/learning/ratings", json={"item_id": item, "stars": stars}
        ).json()

    assert body["rating_count"] == ratings.MIN_SHOWN == 3
    assert body["rating_average"] == 4.0
    # Each learner still sees only their own vote reflected back.
    assert body["my_rating"] == 3


def test_ratings_are_collected_but_never_ranked_on():
    """The chosen stance: collect now, rank later. Curation stays explainable."""
    client.post(
        "/api/learning/progress",
        json={"item_id": "kyc-verifier-walkthrough", "status": "in_progress"},
    )
    before = client.get("/api/learning/curation").json()
    client.post(
        "/api/learning/ratings",
        json={"item_id": "kyc-verifier-walkthrough", "stars": 1},
    )
    after = client.get("/api/learning/curation").json()
    assert before["ranked"] == after["ranked"]
    assert not any("rating" in k for r in after["ranked"] for k in r["components"])

    # It is collected, though: the rating lands in the shared footprint stream
    # that a future ranker reads.
    learning = next(
        p
        for p in client.get("/api/context/summary").json()["by_pillar"]
        if p["pillar"] == "learning"
    )
    assert learning["types"].get("rating") == 1


def test_progress_is_sqlite_and_survives_reads(tmp_path):
    """Progress is mutable state, so it lives in SQLite rather than a rewritten JSON file."""
    import sqlite3

    client.post(
        "/api/learning/progress",
        json={
            "item_id": "prompt-patterns-one-pager",
            "status": "in_progress",
            "progress": 30,
        },
    )
    db = tmp_path / "hub.db"
    assert db.exists()

    rows = (
        sqlite3.connect(db)
        .execute("SELECT user_id, item_id, status, progress FROM learning_progress")
        .fetchall()
    )
    assert ("u-1001", "prompt-patterns-one-pager", "in_progress", 30) in rows

    # concurrent-safe upsert: same row, not a duplicate
    client.post(
        "/api/learning/progress",
        json={"item_id": "prompt-patterns-one-pager", "status": "completed"},
    )
    rows = (
        sqlite3.connect(db)
        .execute("SELECT status, progress FROM learning_progress")
        .fetchall()
    )
    assert len(rows) == 1 and rows[0] == ("completed", 100)


def _agent(**overrides):
    from app.marketplace.models import Agent
    from app.marketplace.store import normalize_agent, store

    base = store.agents[0].model_dump()
    base.update(overrides)
    return Agent.model_validate(normalize_agent(base))


def _compliance():
    from app.marketplace.store import store

    return store.persona("compliance_user")


def test_an_agent_that_names_no_persona_still_ranks_on_its_metadata():
    """Owners describe what an agent does; they should not have to enumerate
    every role that might want it. Curation is derived from that description."""
    from app.marketplace import search

    untagged = _agent(
        id="untagged-screening",
        personas=[],
        business_domains=["Compliance", "Onboarding"],
        capabilities=["Sanctions screening", "Risk scoring"],
        tags=["kyc", "aml"],
    )
    score = search.curation_score(untagged, _compliance())
    assert score > 10, f"metadata-only agent scored {score}"
    assert search.curation_breakdown(untagged, _compliance())["persona_boost"] == 0.0


def test_naming_a_persona_cannot_manufacture_relevance():
    """The boost is a percentage of matched metadata, so 25% of nothing is
    nothing. A mistaken persona tag cannot promote an unrelated agent."""
    from app.marketplace import search

    unrelated = _agent(
        id="unrelated-but-tagged",
        personas=["compliance_user"],
        business_domains=["Engineering"],
        capabilities=["Code review"],
        use_cases=["Review a pull request for style issues"],
        tags=["python"],
        popularity=0,
    )
    parts = search.curation_breakdown(unrelated, _compliance())
    assert parts["persona_boost"] == 0.0
    assert search.curation_score(unrelated, _compliance()) == 0.0


def test_evidence_outranks_a_curator_hint():
    """Real overlap must beat a persona tag sitting on a thin agent -- the
    failure the previous flat +10 produced."""
    from app.marketplace import search

    persona = _compliance()
    thin_but_tagged = _agent(
        id="thin-tagged", personas=["compliance_user"],
        business_domains=["Compliance"], capabilities=[], tags=[], popularity=99,
    )
    rich_untagged = _agent(
        id="rich-untagged", personas=[],
        business_domains=["Compliance", "Onboarding"],
        capabilities=["Sanctions screening"], tags=["kyc"], popularity=0,
    )
    assert search.curation_score(rich_untagged, persona) > search.curation_score(
        thin_but_tagged, persona
    )


def test_capability_matching_tolerates_wording_differences():
    """Two catalogues will not phrase things identically."""
    from app.marketplace import search

    reworded = _agent(
        id="reworded", personas=[], business_domains=[],
        capabilities=["Sanctions list screening"], tags=[], popularity=0,
    )
    assert search.curation_breakdown(reworded, _compliance())["capability"] == 2.0

    unrelated = _agent(
        id="different-customer-thing", personas=[], business_domains=[],
        capabilities=["Customer communication"], tags=[], popularity=0,
    )
    assert search.curation_breakdown(unrelated, _compliance())["capability"] == 0.0


def test_use_cases_count_toward_relevance():
    """An owner's description of what the agent is for is evidence, even when
    the capability list is thin."""
    from app.marketplace import search

    described = _agent(
        id="described-only", personas=[], business_domains=[], capabilities=[], tags=[],
        use_cases=["Screen a customer against sanctions lists"], popularity=0,
    )
    # Covers two interests: the capability "Sanctions screening" and the tag.
    assert search.curation_breakdown(described, _compliance())["use_case"] == 4.0


def test_a_wordy_listing_cannot_outscore_a_precise_one():
    """Coverage is counted per persona interest, not per sentence, so writing
    four use cases about the same thing scores once."""
    from app.marketplace import search

    repetitive = _agent(
        id="repetitive", personas=[], business_domains=[], capabilities=[], tags=[],
        use_cases=[
            "Ask what the policy says",
            "Find the policy section that applies",
            "Look up a policy exception",
            "Explain a policy in plain language",
        ],
        popularity=0,
    )
    broad = _agent(
        id="broad", personas=[], business_domains=[], capabilities=[], tags=[],
        use_cases=["Check a policy", "Screen for sanctions"], popularity=0,  # 3 interests
    )
    parts = search.curation_breakdown(repetitive, _compliance())
    assert parts["use_case"] == 2.0, "one interest, however many sentences"
    assert search.curation_breakdown(broad, _compliance())["use_case"] == 6.0


def test_search_intent_outranks_persona():
    """The two modes are different questions. 'Who are you' drives the
    carousels; 'what do you need right now' must drive search -- a compliance
    user asking about Python gets the code agent, not KYC."""
    results = client.post(
        "/api/marketplace/search",
        json={"query": "I need something to review Python code"},
    ).json()["results"]
    assert results, "expected at least one match"
    assert results[0]["agent"]["id"] == "code-review-assistant"


def test_embedding_text_carries_the_searchable_metadata():
    """Governance fields stay out: the index describes what an agent does, and
    owner, access and URLs are read from agents.json, never from Chroma."""
    from app.marketplace import semantic
    from app.marketplace.store import store

    agent = next(a for a in store.all_agents if a.id == "kyc-risk-screening")
    text = semantic.embedding_text(agent)
    assert agent.name in text
    assert "Sanctions screening" in text and "Compliance" in text
    assert agent.owner.name not in text and agent.owner.email not in text
    assert "http" not in text


def test_agents_are_embedded_once_and_only_re_embedded_when_changed():
    """Embedding is the expensive step, so a restart must not repeat it."""
    from app.marketplace import semantic
    from app.marketplace.store import store

    index = semantic.SemanticIndex()
    agents = store.all_agents
    first = index.sync(agents)
    if not index.available:
        import pytest

        pytest.skip("semantic index unavailable in this environment")
    assert first["added"] == len(agents)

    again = index.sync(agents)
    assert again["unchanged"] == len(agents)
    assert again["added"] == 0 and again["updated"] == 0

    edited = agents[0].model_copy(update={"tagline": "A completely new tagline"})
    third = index.sync([edited, *agents[1:]])
    assert third["updated"] == 1 and third["unchanged"] == len(agents) - 1

    dropped = index.sync(agents[1:])
    assert dropped["removed"] == 1


def test_semantic_retrieval_finds_an_agent_that_shares_no_words():
    """The gap lexical matching cannot close: the KYC agent says "sanctions and
    PEP lists" and never uses the words in this query."""
    from app.marketplace import semantic
    from app.marketplace.store import store

    index = semantic.SemanticIndex()
    index.sync(store.all_agents)
    if not index.available:
        import pytest

        pytest.skip("semantic index unavailable in this environment")
    hits = index.search("anti-money-laundering watchlist checks", limit=3)
    assert hits, "expected candidates"
    assert max(hits, key=hits.get) == "kyc-risk-screening"


def test_search_still_works_when_the_semantic_index_is_disabled(monkeypatch):
    """A failed or switched-off index must degrade to lexical, never 500."""
    monkeypatch.setenv("CREDITWIZ_DISABLE_SEMANTIC", "1")
    from app.marketplace import semantic

    assert semantic.SemanticIndex().search("sanctions screening") == {}
    results = client.post(
        "/api/marketplace/search", json={"query": "validating customer documents"}
    ).json()["results"]
    assert results and results[0]["agent"]["id"] == "kyc-document-verifier"


def test_search_records_a_trace_that_explains_the_ranking():
    """Afterwards it must be possible to tell whether an agent was missed
    because retrieval never proposed it or because the ranker dropped it."""
    client.post(
        "/api/marketplace/search",
        json={"query": "anti-money-laundering watchlist checks"},
    )
    trace = client.get(
        "/api/context/events?pillar=marketplace&type=search&limit=1"
    ).json()[0]
    assert trace["query"] == "anti-money-laundering watchlist checks"
    assert trace["persona"] == "compliance_user"

    meta = trace["meta"]
    assert meta["engine"] in {"claude", "local"}
    assert meta["results"] and set(meta["scores"]) == set(meta["results"])
    assert "domains" in meta["intent"] and "capabilities" in meta["intent"]
    assert "available" in meta["retrieval"] and "candidates" in meta["retrieval"]
    assert meta["no_match"] is False
    assert isinstance(meta["took_ms"], int)


def test_the_footprint_trail_is_scoped_to_the_signed_in_user():
    client.post("/api/marketplace/search", json={"query": "sanctions screening"})
    assert client.get("/api/context/events").json(), "own trail is readable"

    # Switching the session swaps the cookie, so this reads the other user's trail.
    assert (
        client.post("/api/auth/demo", json={"user_id": "demo-developer"}).status_code
        == 200
    )
    theirs = [
        e.get("query") for e in client.get("/api/context/events?type=search").json()
    ]
    assert "sanctions screening" not in theirs
