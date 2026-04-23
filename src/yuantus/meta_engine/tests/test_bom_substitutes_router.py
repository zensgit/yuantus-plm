"""
Direct route behavior tests for bom_substitutes_router (BOM R6 slice).

Covers the 3 endpoints moved out of bom_router.py by R6:
  - GET    /api/v1/bom/{bom_line_id}/substitutes
  - POST   /api/v1/bom/{bom_line_id}/substitutes
  - DELETE /api/v1/bom/{bom_line_id}/substitutes/{substitute_id}
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.suspended_guard import SuspendedStateError
from yuantus.meta_engine.web.bom_substitutes_router import bom_substitutes_router


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
    app.include_router(bom_substitutes_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def _bom_line(item_type_id="Part BOM", source_id=None):
    return SimpleNamespace(
        id="BOM-LINE-1",
        item_type_id=item_type_id,
        source_id=source_id,
        state="Draft",
    )


def test_list_substitutes_bom_line_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.get("/api/v1/bom/BOM-LINE-1/substitutes")
    assert response.status_code == 404
    assert response.json()["detail"] == "BOM line BOM-LINE-1 not found"


def test_list_substitutes_invalid_line_type_returns_400(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line(item_type_id="Document")
    response = client.get("/api/v1/bom/BOM-LINE-1/substitutes")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid BOM line type"


def test_list_substitutes_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.get("/api/v1/bom/BOM-LINE-1/substitutes")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_list_substitutes_success_returns_count_and_entries(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_substitutes_router.SubstituteService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.get_bom_substitutes.return_value = [
            {
                "id": "SUB-REL-1",
                "relationship": {"id": "SUB-REL-1"},
                "rank": 10,
                "substitute_number": "P-ALT",
            }
        ]
        response = client.get("/api/v1/bom/BOM-LINE-1/substitutes")

    assert response.status_code == 200
    body = response.json()
    assert body["bom_line_id"] == "BOM-LINE-1"
    assert body["count"] == 1
    assert body["substitutes"][0]["id"] == "SUB-REL-1"
    mock_service.return_value.get_bom_substitutes.assert_called_once_with("BOM-LINE-1")


def test_add_substitute_add_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.post(
            "/api/v1/bom/BOM-LINE-1/substitutes",
            json={"substitute_item_id": "SUB-1"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_add_substitute_parent_locked_returns_409(client, mock_db_session):
    parent = SimpleNamespace(id="PARENT-1", item_type_id="Part", state="Frozen")

    def get_side_effect(_model, item_id):
        return {
            "BOM-LINE-1": _bom_line(source_id="PARENT-1"),
            "PARENT-1": parent,
            "Part": SimpleNamespace(id="Part"),
        }.get(item_id)

    mock_db_session.get.side_effect = get_side_effect
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_substitutes_router.is_item_locked",
        return_value=(True, "Frozen"),
    ):
        mock_perm.return_value.check_permission.return_value = True
        response = client.post(
            "/api/v1/bom/BOM-LINE-1/substitutes",
            json={"substitute_item_id": "SUB-1"},
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "Item is locked in state 'Frozen'"


def test_add_substitute_not_latest_and_suspended_map_to_409(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    cases = [
        NotLatestReleasedError(reason="not_latest_released", target_id="SUB-1"),
        SuspendedStateError(reason="target_suspended", target_id="SUB-1"),
    ]

    for exc in cases:
        with patch(
            "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
        ) as mock_perm, patch(
            "yuantus.meta_engine.web.bom_substitutes_router.SubstituteService"
        ) as mock_service:
            mock_perm.return_value.check_permission.return_value = True
            mock_service.return_value.add_substitute.side_effect = exc
            response = client.post(
                "/api/v1/bom/BOM-LINE-1/substitutes",
                json={"substitute_item_id": "SUB-1"},
            )
        assert response.status_code == 409
        assert mock_db_session.rollback.called
        mock_db_session.rollback.reset_mock()


def test_add_substitute_value_error_mapping(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    cases = [
        ("Invalid BOM Line: nope", 404),
        ("duplicate substitute", 400),
    ]

    for message, expected_status in cases:
        with patch(
            "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
        ) as mock_perm, patch(
            "yuantus.meta_engine.web.bom_substitutes_router.SubstituteService"
        ) as mock_service:
            mock_perm.return_value.check_permission.return_value = True
            mock_service.return_value.add_substitute.side_effect = ValueError(message)
            response = client.post(
                "/api/v1/bom/BOM-LINE-1/substitutes",
                json={"substitute_item_id": "SUB-1"},
            )
        assert response.status_code == expected_status
        assert response.json()["detail"] == message


def test_add_substitute_success_returns_relationship_id(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_substitutes_router.SubstituteService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.add_substitute.return_value = SimpleNamespace(id="SUB-REL-1")
        response = client.post(
            "/api/v1/bom/BOM-LINE-1/substitutes",
            json={"substitute_item_id": "SUB-1", "properties": {"rank": 20}},
        )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "substitute_id": "SUB-REL-1",
        "bom_line_id": "BOM-LINE-1",
        "substitute_item_id": "SUB-1",
    }
    mock_service.return_value.add_substitute.assert_called_once_with(
        bom_line_id="BOM-LINE-1",
        substitute_item_id="SUB-1",
        properties={"rank": 20},
        user_id=1,
    )


def test_remove_substitute_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.delete("/api/v1/bom/BOM-LINE-1/substitutes/SUB-REL-1")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_remove_substitute_value_error_maps_to_404(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_substitutes_router.SubstituteService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.remove_substitute.side_effect = ValueError("missing")
        response = client.delete("/api/v1/bom/BOM-LINE-1/substitutes/SUB-REL-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "missing"


def test_remove_substitute_success_returns_removed_id(client, mock_db_session):
    mock_db_session.get.return_value = _bom_line()
    with patch(
        "yuantus.meta_engine.web.bom_substitutes_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_substitutes_router.SubstituteService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        response = client.delete("/api/v1/bom/BOM-LINE-1/substitutes/SUB-REL-1")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "substitute_id": "SUB-REL-1"}
    mock_service.return_value.remove_substitute.assert_called_once_with(
        "SUB-REL-1",
        user_id=1,
    )

