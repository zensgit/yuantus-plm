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


def test_apply_diagnostics_reports_activity_blockers_as_structured_error():
    client, _db = _client_with_user_id(1)

    eco = SimpleNamespace(id="eco-1")

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = eco
        service.get_apply_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {
                    "code": "eco_activity_blockers_present",
                    "message": "Activity gate blockers: ['act-1']",
                    "rule_id": "eco.activity_blockers_clear",
                    "details": {"eco_id": "eco-1"},
                }
            ],
            "warnings": [],
        }

        resp = client.get("/api/v1/eco/eco-1/apply-diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "eco_activity_blockers_present"
    assert data["errors"][0]["rule_id"] == "eco.activity_blockers_clear"


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


def test_compute_changes_passes_compare_mode_to_service():
    client, db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.compute_bom_changes.return_value = [
            SimpleNamespace(
                to_dict=lambda: {
                    "id": "chg-1",
                    "eco_id": "eco-1",
                    "change_type": "update",
                    "relationship_item_id": "rel-1",
                }
            )
        ]

        resp = client.post("/api/v1/eco/eco-1/compute-changes?compare_mode=summarized")

    assert resp.status_code == 200
    assert resp.json()[0]["change_type"] == "update"
    assert db.commit.called
    service.compute_bom_changes.assert_called_once_with(
        "eco-1",
        compare_mode="summarized",
    )


def test_compute_changes_invalid_compare_mode_maps_to_400():
    client, _db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service_cls.return_value.compute_bom_changes.side_effect = ValueError(
            "compare_mode must be one of: only_product, summarized, by_item"
        )

        resp = client.post("/api/v1/eco/eco-1/compute-changes?compare_mode=bad-mode")

    assert resp.status_code == 400
    assert "compare_mode must be one of" in (resp.json().get("detail") or "")


def test_suspend_endpoint_commits_and_returns_eco():
    client, db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.action_suspend.return_value = SimpleNamespace(
            to_dict=lambda: {
                "id": "eco-1",
                "state": "suspended",
                "kanban_state": "blocked",
            }
        )

        resp = client.post(
            "/api/v1/eco/eco-1/suspend",
            json={"reason": "awaiting supplier response"},
        )

    assert resp.status_code == 200
    assert resp.json()["state"] == "suspended"
    assert db.commit.called
    service.action_suspend.assert_called_once_with(
        "eco-1",
        1,
        "awaiting supplier response",
    )


def test_unsuspend_endpoint_passes_resume_state_to_service():
    client, db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.action_unsuspend.return_value = SimpleNamespace(
            to_dict=lambda: {
                "id": "eco-1",
                "state": "approved",
                "kanban_state": "normal",
            }
        )

        resp = client.post(
            "/api/v1/eco/eco-1/unsuspend",
            json={"resume_state": "approved"},
        )

    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"
    assert db.commit.called
    service.action_unsuspend.assert_called_once_with(
        "eco-1",
        1,
        resume_state="approved",
    )


def test_unsuspend_diagnostics_200_when_eco_missing():
    client, _db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = None
        service.get_unsuspend_diagnostics.return_value = {
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

        resp = client.get("/api/v1/eco/eco-404/unsuspend-diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["resource_id"] == "eco-404"
    assert data["errors"][0]["code"] == "eco_not_found"


def test_unsuspend_endpoint_blocks_when_diagnostics_errors_present():
    client, _db = _client_with_user_id(1)

    eco = SimpleNamespace(id="eco-1")

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = eco
        service.get_unsuspend_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [
                {
                    "code": "eco_activity_blockers_present",
                    "message": "ECO activity blockers detected: act-1",
                    "rule_id": "eco.activity_blockers_clear",
                    "details": {"eco_id": "eco-1"},
                }
            ],
            "warnings": [],
        }
        service.action_unsuspend = MagicMock(
            return_value=SimpleNamespace(
                to_dict=lambda: {
                    "id": "eco-1",
                    "state": "progress",
                }
            )
        )

        resp = client.post("/api/v1/eco/eco-1/unsuspend", json={})

    assert resp.status_code == 400
    assert "ECO unsuspend blocked" in (resp.json().get("detail") or "")
    assert service.action_unsuspend.call_count == 0


def test_unsuspend_endpoint_force_bypasses_diagnostics():
    client, db = _client_with_user_id(1)

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.action_unsuspend.return_value = SimpleNamespace(
            to_dict=lambda: {
                "id": "eco-1",
                "state": "progress",
                "kanban_state": "normal",
            }
        )

        resp = client.post("/api/v1/eco/eco-1/unsuspend?force=true", json={})

    assert resp.status_code == 200
    assert resp.json()["state"] == "progress"
    assert db.commit.called
    assert service.get_unsuspend_diagnostics.call_count == 0
    service.action_unsuspend.assert_called_once_with(
        "eco-1",
        1,
        resume_state=None,
    )
