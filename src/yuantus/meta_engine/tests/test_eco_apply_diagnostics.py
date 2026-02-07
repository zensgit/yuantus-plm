from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError


def _client_with_user_id(user_id: int):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_user_id():
        return user_id

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db_session


def test_apply_diagnostics_200_when_eco_missing():
    client, _db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = None
        service.get_apply_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {
                    "code": "eco_not_found",
                    "message": "ECO not found: eco-404",
                    "rule_id": "eco.exists",
                    "details": {"eco_id": "eco-404"},
                }
            ],
            "warnings": [],
        }

        resp = client.get("/api/v1/eco/eco-404/apply-diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["resource_type"] == "eco"
    assert data["resource_id"] == "eco-404"
    assert data["errors"][0]["code"] == "eco_not_found"


def test_apply_diagnostics_denies_when_permission_check_fails():
    client, _db = _client_with_user_id(2)

    eco = SimpleNamespace(id="eco-1")

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = eco
        service.permission_service.check_permission.side_effect = PermissionError(
            action="execute", resource="ECO"
        )

        resp = client.get("/api/v1/eco/eco-1/apply-diagnostics")

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"


def test_apply_endpoint_blocks_when_diagnostics_errors_present():
    client, _db = _client_with_user_id(1)

    eco = SimpleNamespace(id="eco-1")

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = eco
        service.get_apply_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {
                    "code": "eco_not_approved",
                    "message": "ECO not approved",
                    "rule_id": "eco.state_approved",
                    "details": {"eco_id": "eco-1"},
                }
            ],
            "warnings": [],
        }
        service.action_apply = MagicMock(return_value=True)

        resp = client.post("/api/v1/eco/eco-1/apply")

    assert resp.status_code == 400
    assert "ECO apply blocked" in (resp.json().get("detail") or "")
    assert service.action_apply.call_count == 0


def test_apply_endpoint_force_bypasses_diagnostics():
    client, _db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.action_apply = MagicMock(return_value=True)

        resp = client.post("/api/v1/eco/eco-1/apply?force=true")

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert service.action_apply.call_count == 1

