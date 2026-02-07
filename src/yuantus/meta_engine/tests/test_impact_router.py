from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item


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
    return TestClient(app), mock_db_session


def test_impact_summary_404_when_item_missing():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    db.get.return_value = None

    resp = client.get("/api/v1/impact/items/item-1/summary")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_impact_summary_denies_without_read_permission():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, db = _client_with_user(user)
    db.get.return_value = Item(id="item-1", item_type_id="Part", properties={}, state="released")

    perm = MagicMock()
    perm.check_permission.return_value = False

    with patch("yuantus.meta_engine.web.impact_router.MetaPermissionService", return_value=perm):
        resp = client.get("/api/v1/impact/items/item-1/summary")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"


def test_impact_summary_returns_domain_summaries():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    db.get.return_value = Item(id="item-1", item_type_id="Part", properties={}, state="released")

    perm = MagicMock()
    perm.check_permission.return_value = True

    impact = MagicMock()
    impact.where_used_summary.return_value = {
        "total": 2,
        "hits": [
            {"parent_id": "p1", "parent_number": "P-1", "parent_name": "Parent1", "relationship_id": "rel-1", "level": 1, "line": {"quantity": 1}},
        ],
        "recursive": False,
        "max_levels": 10,
    }
    impact.baselines_summary.return_value = {
        "total": 1,
        "hits": [
            {"baseline_id": "bl-1", "name": "BL1", "baseline_number": "BL-001", "baseline_type": "bom", "scope": "product", "state": "draft", "root_item_id": "root-1", "created_at": None, "released_at": None},
        ],
    }
    impact.esign_summary.return_value = {
        "total": 3,
        "valid": 2,
        "revoked": 1,
        "expired": 0,
        "latest_signed_at": None,
        "latest_signatures": [],
        "latest_manifest": None,
    }

    with (
        patch("yuantus.meta_engine.web.impact_router.MetaPermissionService", return_value=perm),
        patch("yuantus.meta_engine.web.impact_router.ImpactAnalysisService", return_value=impact),
    ):
        resp = client.get("/api/v1/impact/items/item-1/summary")

    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == "item-1"
    assert data["where_used"]["total"] == 2
    assert data["baselines"]["total"] == 1
    assert data["esign"]["total"] == 3

