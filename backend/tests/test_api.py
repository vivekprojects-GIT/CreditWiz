from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_home_has_nine_pillars_with_three_priority():
    body = client.get("/api/home").json()
    assert body["user"]["first_name"] == "Sai"
    assert len(body["pillars"]) == 9
    priority = [p["id"] for p in body["pillars"] if p["priority"]]
    assert priority == ["marketplace", "learning", "community"]


def test_search_matches_title_and_kind():
    body = client.get("/api/search", params={"q": "agent"}).json()
    kinds = {r["kind"] for r in body["results"]}
    assert kinds == {"agent", "learning"}
    assert client.get("/api/search", params={"q": ""}).json()["results"] == []


def test_pillar_detail_and_404():
    body = client.get("/api/pillars/learning").json()
    assert body["title"] == "AI Learning and Enablement"
    assert len(body["sections"]) == 6
    assert client.get("/api/pillars/nope").status_code == 404


def test_notifications_match_unread_count():
    notes = client.get("/api/notifications").json()
    me = client.get("/api/me").json()
    assert len([n for n in notes if not n["read"]]) == me["unread_notifications"]


def test_persona_is_derived_from_role_not_stored():
    me = client.get("/api/me").json()
    assert me["job_title"] == "Compliance Analyst"
    assert me["persona"]["id"] == "compliance_user"
    assert me["persona"]["derived_from"] == "role"
    assert "persona" not in __import__("json").load(
        open("data/user.json", encoding="utf-8")
    )


def test_persona_mapping_rules():
    from app.identity import DirectoryProfile, derive_persona

    base = dict(id="x", name="X Y", first_name="X", initials="XY")
    assert (
        derive_persona(
            DirectoryProfile(**base, job_title="Senior Compliance Analyst")
        ).id
        == "compliance_user"
    )
    assert (
        derive_persona(DirectoryProfile(**base, job_title="Software Engineer")).id
        == "developer"
    )
    dept = derive_persona(
        DirectoryProfile(**base, job_title="Associate", department="Collections")
    )
    assert dept.id == "operations_user" and dept.derived_from == "department"
    default = derive_persona(
        DirectoryProfile(**base, job_title="Astronaut", department="Space")
    )
    assert default.id == "business_user" and default.derived_from == "default"


def test_marketplace_defaults_to_derived_persona():
    body = client.get("/api/marketplace/home").json()
    assert body["persona"] == "compliance_user"
