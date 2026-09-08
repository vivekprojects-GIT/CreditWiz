import pytest
from app import auth, database
from app.learning.store import store as learning_store


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch, request):
    monkeypatch.setenv("CREDITWIZ_ENV", "development")
    monkeypatch.setenv("CREDITWIZ_DISABLE_LLM", "1")
    monkeypatch.setattr(database, "VAR_DIR", tmp_path)
    database._ready.discard(str((tmp_path / "hub.db").resolve()))
    learning_store.invalidate()
    auth.seed_users()
    token = auth.current_id.set("u-1001")
    client = getattr(request.module, "client", None)
    if client:
        client.cookies.clear()
        client.headers["X-CreditWiz-Request"] = "1"
        assert (
            client.post("/api/auth/demo", json={"user_id": "u-1001"}).status_code == 200
        )
    yield
    if client:
        client.cookies.clear()
    auth.current_id.reset(token)
