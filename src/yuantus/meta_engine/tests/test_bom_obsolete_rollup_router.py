from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.bom_router import bom_router


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
    app.include_router(bom_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def test_obsolete_scan_not_found(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.get("/api/v1/bom/NOPE/obsolete")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item NOPE not found"


def test_obsolete_resolve_value_error_returns_400(client, mock_db_session):
    mock_db_session.get.return_value = MagicMock()
    with patch(
        "yuantus.meta_engine.web.bom_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = True
        with patch(
            "yuantus.meta_engine.web.bom_router.BOMObsoleteService"
        ) as mock_service:
            mock_service.return_value.resolve.side_effect = ValueError("bad mode")
            response = client.post(
                "/api/v1/bom/ROOT/obsolete/resolve",
                json={},
            )
    assert response.status_code == 400
    assert response.json()["detail"] == "bad mode"
    assert mock_db_session.rollback.called


def test_weight_rollup_write_back_permission_denied(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.side_effect = [True, False]
        response = client.post(
            "/api/v1/bom/ROOT/rollup/weight",
            json={"write_back": True},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_remove_child_ambiguous_uom_returns_400(client, mock_db_session):
    parent = MagicMock()
    parent.item_type_id = "Part"
    mock_db_session.get.return_value = parent

    with patch("yuantus.meta_engine.web.bom_router.MetaPermissionService") as mock_perm, patch(
        "yuantus.meta_engine.web.bom_router.is_item_locked",
        return_value=(False, None),
    ), patch("yuantus.meta_engine.web.bom_router.BOMService") as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.remove_child.side_effect = ValueError(
            "Multiple BOM relationships found: parent-1 -> child-1; specify uom (EA, MM)"
        )
        response = client.delete("/api/v1/bom/parent-1/children/child-1")

    assert response.status_code == 400
    assert "specify uom" in response.json()["detail"]
    assert mock_db_session.rollback.called


def test_remove_child_forwards_optional_uom(client, mock_db_session):
    parent = MagicMock()
    parent.item_type_id = "Part"
    mock_db_session.get.return_value = parent

    with patch("yuantus.meta_engine.web.bom_router.MetaPermissionService") as mock_perm, patch(
        "yuantus.meta_engine.web.bom_router.is_item_locked",
        return_value=(False, None),
    ), patch("yuantus.meta_engine.web.bom_router.BOMService") as mock_service:
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
