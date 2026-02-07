from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
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


def test_release_diagnostics_200_when_baseline_missing():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = None
        service.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {
                    "code": "baseline_not_found",
                    "message": "Baseline not found: bl-404",
                    "rule_id": "baseline.exists",
                    "details": {"baseline_id": "bl-404"},
                }
            ],
            "warnings": [],
        }

        resp = client.get("/api/v1/baselines/bl-404/release-diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["resource_type"] == "baseline"
    assert data["resource_id"] == "bl-404"
    assert data["errors"][0]["code"] == "baseline_not_found"


def test_release_diagnostics_denies_when_user_cannot_read_root_item():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")
    db.get.return_value = Item(id="item-1", item_type_id="Part", properties={}, state="released")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service._ensure_can_read.side_effect = PermissionError(action="get", resource="Part")

        resp = client.get("/api/v1/baselines/bl-1/release-diagnostics")

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_release_diagnostics_returns_member_missing_item_error():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {
                    "code": "baseline_member_missing_item",
                    "message": "Item not found: P-404",
                    "rule_id": "baseline.members_references_exist",
                    "details": {"member_id": "m-1", "item_number": "P-404"},
                }
            ],
            "warnings": [],
        }

        resp = client.get("/api/v1/baselines/bl-1/release-diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "baseline_member_missing_item"


def test_release_diagnostics_returns_unreleased_item_warning():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [],
            "warnings": [
                {
                    "code": "baseline_item_not_released",
                    "message": "Item P-1 is not released (state: New)",
                    "rule_id": "baseline.warnings_for_unreleased_or_changed_members",
                    "details": {"item_number": "P-1", "item_state": "New"},
                }
            ],
        }

        resp = client.get("/api/v1/baselines/bl-1/release-diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["warnings"][0]["code"] == "baseline_item_not_released"


def test_release_blocks_when_diagnostics_has_errors():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {"code": "baseline_member_missing_item", "message": "Item not found", "rule_id": "x"},
            ],
            "warnings": [],
        }

        resp = client.post("/api/v1/baselines/bl-1/release?ruleset_id=default", json={"force": False})

        assert service.release_baseline.called is False

    assert resp.status_code == 400
    assert "blocked" in resp.json()["detail"].lower()
    assert "errors=" in resp.json()["detail"]


def test_force_release_bypasses_diagnostics_and_calls_release():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")
    released = SimpleNamespace(
        id="bl-1",
        name="BL1",
        description=None,
        baseline_type="bom",
        baseline_number="BL-001",
        scope="product",
        eco_id=None,
        root_item_id="item-1",
        root_version_id=None,
        root_config_id="P-1",
        max_levels=10,
        effective_at=None,
        include_bom=True,
        include_substitutes=False,
        include_effectivity=False,
        include_documents=False,
        include_relationships=False,
        line_key="child_config",
        item_count=0,
        relationship_count=0,
        state="released",
        is_validated=True,
        validation_errors=None,
        validated_at=None,
        validated_by_id=None,
        is_locked=True,
        locked_at=None,
        released_at=None,
        released_by_id=1,
        created_at=None,
        created_by_id=1,
        snapshot=None,
    )

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service.release_baseline.return_value = released

        resp = client.post("/api/v1/baselines/bl-1/release?ruleset_id=default", json={"force": True})

        assert service.get_release_diagnostics.called is False
        assert service.release_baseline.called is True

    assert resp.status_code == 200
    assert resp.json()["state"] == "released"


def test_release_diagnostics_returns_400_on_unknown_ruleset():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service.get_release_diagnostics.side_effect = ValueError(
            "Unknown release ruleset: kind=baseline_release, ruleset_id=missing, known=default"
        )

        resp = client.get("/api/v1/baselines/bl-1/release-diagnostics?ruleset_id=missing")

    assert resp.status_code == 400
    assert "unknown release ruleset" in resp.json()["detail"].lower()


def test_release_diagnostics_returns_400_on_unknown_rule_id_in_config():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    baseline = SimpleNamespace(id="bl-1", created_by_id=1, root_item_id="item-1")

    with patch("yuantus.meta_engine.web.baseline_router.BaselineService") as service_cls:
        service = service_cls.return_value
        service.get_baseline.return_value = baseline
        service.get_release_diagnostics.side_effect = ValueError(
            "Invalid YUANTUS_RELEASE_VALIDATION_RULESETS_JSON: baseline_release.default contains unknown rule ids: baseline.nope"
        )

        resp = client.get("/api/v1/baselines/bl-1/release-diagnostics?ruleset_id=default")

    assert resp.status_code == 400
    assert "invalid yuantus_release_validation_rulesets_json" in resp.json()["detail"].lower()

