from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.baseline import BaselineComparison
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


def test_validate_baseline_denies_when_user_cannot_read_root_item():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")
    db.get.return_value = Item(id="item-1", item_type_id="Part", properties={}, state="released")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service._ensure_can_read.side_effect = PermissionError(action="get", resource="Part")

        resp = client.post("/api/v1/baselines/bl-1/validate")

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_release_baseline_denies_when_user_cannot_read_root_item():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")
    db.get.return_value = Item(id="item-1", item_type_id="Part", properties={}, state="released")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service._ensure_can_read.side_effect = PermissionError(action="get", resource="Part")

        resp = client.post("/api/v1/baselines/bl-1/release", json={"force": False})

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_compare_baseline_denies_when_user_cannot_read_root_item():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1", line_key="child_config")
    db.get.return_value = Item(id="item-1", item_type_id="Part", properties={}, state="released")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service._ensure_can_read.side_effect = PermissionError(action="get", resource="Part")

        resp = client.post(
            "/api/v1/baselines/bl-1/compare",
            json={"target_type": "item", "target_id": "item-2"},
        )

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_get_comparison_details_denies_when_user_cannot_read_source_baseline():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, db = _client_with_user(user)

    comparison = SimpleNamespace(id="cmp-1", baseline_a_id="bl-a", baseline_b_id="bl-b")
    baseline_a = SimpleNamespace(id="bl-a", created_by_id=1, root_item_id="item-a")
    baseline_b = SimpleNamespace(id="bl-b", created_by_id=1, root_item_id="item-b")

    def _db_get(model, key):
        if model is BaselineComparison and key == "cmp-1":
            return comparison
        if model is Item and key in {"item-a", "item-b"}:
            return Item(id=key, item_type_id="Part", properties={}, state="released")
        return None

    db.get.side_effect = _db_get

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.side_effect = lambda baseline_id: {
            "bl-a": baseline_a,
            "bl-b": baseline_b,
        }.get(baseline_id)
        service._ensure_can_read.side_effect = PermissionError(action="get", resource="Part")

        resp = client.get("/api/v1/baselines/comparisons/cmp-1/details")

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"

