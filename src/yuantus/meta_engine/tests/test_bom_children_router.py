"""
Direct route behavior tests for bom_children_router (BOM R3 slice).

Covers the 2 endpoints moved out of bom_router.py by R3:
  - POST   /api/v1/bom/{parent_id}/children
  - DELETE /api/v1/bom/{parent_id}/children/{child_id}

Uses the isolated-router test pattern (FastAPI + include_router) so the
AuthEnforcementMiddleware is not in the stack -- no AUTH_MODE=optional fixture
needed.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.bom_service import CycleDetectedError
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.suspended_guard import SuspendedStateError
from yuantus.meta_engine.web.bom_children_router import bom_children_router


def _current_user() -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        is_superuser=True,
    )


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def client(mock_db_session):
    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(bom_children_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def _parent() -> SimpleNamespace:
    return SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft")


def test_add_child_parent_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.post("/api/v1/bom/MISSING/children", json={"child_id": "child-1"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Item MISSING not found"


def test_add_child_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _parent()
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_add_child_locked_parent_returns_409(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(True, "Released"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Item is locked in state 'Released'"


def test_add_child_forwards_payload_and_commits(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.add_child.return_value = {
            "ok": True,
            "relationship_id": "rel-1",
            "parent_id": "parent-1",
            "child_id": "child-1",
            "effectivity_id": "eff-1",
        }
        response = client.post(
            "/api/v1/bom/parent-1/children",
            json={
                "child_id": "child-1",
                "quantity": 2.5,
                "uom": "mm",
                "find_num": "10",
                "refdes": "R1",
                "effectivity_from": "2026-04-23T00:00:00",
                "effectivity_to": "2026-04-24T00:00:00",
                "config_condition": {"region": "EU"},
                "extra_properties": {"note": "x"},
            },
        )
    assert response.status_code == 200
    assert response.json()["relationship_id"] == "rel-1"
    called = mock_service.return_value.add_child.call_args.kwargs
    assert called["parent_id"] == "parent-1"
    assert called["child_id"] == "child-1"
    assert called["user_id"] == 1
    assert called["quantity"] == 2.5
    assert called["uom"] == "mm"
    assert called["find_num"] == "10"
    assert called["refdes"] == "R1"
    assert called["effectivity_from"].year == 2026
    assert called["effectivity_to"].day == 24
    assert called["config_condition"] == {"region": "EU"}
    assert called["extra_properties"] == {"note": "x"}
    assert mock_db_session.commit.called


def test_add_child_cycle_detected_returns_409_json_response(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.add_child",
        side_effect=CycleDetectedError("parent-1", "child-1", ["parent-1", "child-1"]),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})
    assert response.status_code == 409
    assert response.json()["error"] == "CYCLE_DETECTED"
    assert mock_db_session.rollback.called


def test_add_child_not_latest_released_returns_409(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.add_child",
        side_effect=NotLatestReleasedError(reason="not_latest_released", target_id="child-1"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "NOT_LATEST_RELEASED"
    assert mock_db_session.rollback.called


def test_add_child_suspended_state_returns_409(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.add_child",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="child-1"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "SUSPENDED_STATE"
    assert mock_db_session.rollback.called


def test_add_child_value_error_returns_400(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.add_child",
        side_effect=ValueError("bad child"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})
    assert response.status_code == 400
    assert response.json()["detail"] == "bad child"
    assert mock_db_session.rollback.called


def test_remove_child_parent_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.delete("/api/v1/bom/MISSING/children/child-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item MISSING not found"


def test_remove_child_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _parent()
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.delete("/api/v1/bom/parent-1/children/child-1")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_remove_child_locked_parent_returns_409(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(True, "Released"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.delete("/api/v1/bom/parent-1/children/child-1")
    assert response.status_code == 409
    assert response.json()["detail"] == "Item is locked in state 'Released'"


def test_remove_child_forwards_optional_uom_and_commits(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.remove_child.return_value = {
            "ok": True,
            "relationship_id": "rel-mm",
        }
        response = client.delete("/api/v1/bom/parent-1/children/child-1?uom=mm")
    assert response.status_code == 200
    assert response.json()["relationship_id"] == "rel-mm"
    mock_service.return_value.remove_child.assert_called_once_with(
        parent_id="parent-1",
        child_id="child-1",
        uom="mm",
    )
    assert mock_db_session.commit.called


def test_remove_child_ambiguous_uom_returns_400(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.remove_child.side_effect = ValueError(
            "Multiple BOM relationships found: parent-1 -> child-1; specify uom (EA, MM)"
        )
        response = client.delete("/api/v1/bom/parent-1/children/child-1")
    assert response.status_code == 400
    assert "specify uom" in response.json()["detail"]
    assert mock_db_session.rollback.called


def test_remove_child_other_value_error_returns_404(client, mock_db_session):
    mock_db_session.get.side_effect = lambda model, item_id: {
        "parent-1": _parent(),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    with patch(
        "yuantus.meta_engine.web.bom_children_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.remove_child",
        side_effect=ValueError("relationship not found"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.delete("/api/v1/bom/parent-1/children/child-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "relationship not found"
    assert mock_db_session.rollback.called
