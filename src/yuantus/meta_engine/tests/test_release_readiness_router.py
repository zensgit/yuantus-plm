from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item


def _client_with_user(user, *, item_exists: bool):
    mock_db_session = MagicMock()
    mock_db_session.get.return_value = (
        Item(id="item-1", item_type_id="Part", properties={}, state="draft")
        if item_exists
        else None
    )

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
    return TestClient(app), mock_db_session


def test_release_readiness_denies_non_admin():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=True)

    resp = client.get("/api/v1/release-readiness/items/item-1")
    assert resp.status_code == 403


def test_release_readiness_returns_404_when_item_missing():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=False)

    resp = client.get("/api/v1/release-readiness/items/item-404")
    assert resp.status_code == 404


def test_release_readiness_returns_aggregated_diagnostics():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=True)

    payload = {
        "item_id": "item-1",
        "ruleset_id": "readiness",
        "summary": {
            "ok": False,
            "resources": 1,
            "ok_resources": 0,
            "error_count": 1,
            "warning_count": 0,
            "by_kind": {
                "mbom_release": {
                    "resources": 1,
                    "ok_resources": 0,
                    "error_count": 1,
                    "warning_count": 0,
                }
            },
        },
        "resources": [
            {
                "kind": "mbom_release",
                "resource_type": "mbom",
                "resource_id": "mbom-1",
                "name": "MBOM 1",
                "state": "draft",
                "ruleset_id": "readiness",
                "errors": [
                    {
                        "code": "mbom_empty_structure",
                        "message": "MBOM structure is empty: mbom-1",
                        "rule_id": "mbom.has_non_empty_structure",
                        "details": {"mbom_id": "mbom-1"},
                    }
                ],
                "warnings": [],
            }
        ],
        "esign_manifest": None,
    }

    with patch("yuantus.meta_engine.web.release_readiness_router.ReleaseReadinessService") as cls:
        svc = cls.return_value
        svc.get_item_release_readiness.return_value = payload

        resp = client.get("/api/v1/release-readiness/items/item-1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == "item-1"
    assert data["ruleset_id"] == "readiness"
    assert data["summary"]["ok"] is False
    assert data["resources"][0]["kind"] == "mbom_release"
    assert data["resources"][0]["diagnostics"]["errors"][0]["code"] == "mbom_empty_structure"

