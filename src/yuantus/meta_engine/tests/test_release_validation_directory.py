import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.config.settings import get_settings
from yuantus.database import get_db


def _client_with_user(user):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def test_ruleset_directory_lists_builtin_kinds_and_readiness_rulesets():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client = _client_with_user(user)

    resp = client.get("/api/v1/release-validation/rulesets")
    assert resp.status_code == 200

    data = resp.json()
    kinds = {k["kind"] for k in data["kinds"]}
    assert "routing_release" in kinds
    assert "mbom_release" in kinds
    assert "baseline_release" in kinds
    assert "eco_apply" in kinds

    routing_kind = next(k for k in data["kinds"] if k["kind"] == "routing_release")
    ruleset_ids = {r["ruleset_id"] for r in routing_kind["rulesets"]}
    assert "default" in ruleset_ids
    assert "readiness" in ruleset_ids


def test_ruleset_directory_rejects_unknown_rule_ids(monkeypatch):
    monkeypatch.setenv(
        "YUANTUS_RELEASE_VALIDATION_RULESETS_JSON",
        json.dumps(
            {
                "routing_release": {
                    "bad": ["routing.exists", "routing.unknown_rule_id"],
                }
            }
        ),
    )
    get_settings.cache_clear()

    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client = _client_with_user(user)

    resp = client.get("/api/v1/release-validation/rulesets")
    assert resp.status_code == 400
    assert "unknown rule ids" in (resp.json().get("detail") or "")

    get_settings.cache_clear()

