"""
Direct route behavior tests for bom_where_used_router (BOM R5 slice).

Covers the 2 endpoints moved out of bom_router.py by R5:
  - GET /api/v1/bom/{item_id}/where-used
  - GET /api/v1/bom/where-used/schema

Uses an isolated FastAPI app with dependency overrides, matching the router
decomposition tests for R2-R4.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.bom_where_used_router import bom_where_used_router


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
    app.include_router(bom_where_used_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def test_where_used_item_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.get("/api/v1/bom/NOPE/where-used")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item NOPE not found"


def test_where_used_item_permission_denied_returns_403(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_where_used_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.get("/api/v1/bom/ITEM-1/where-used")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_where_used_bom_permission_denied_returns_403(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_where_used_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.side_effect = [True, False]
        response = client.get("/api/v1/bom/ITEM-1/where-used")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_where_used_success_forwards_parameters_and_normalizes_line_defaults(
    client, mock_db_session
):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_where_used_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_where_used_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.get_where_used.return_value = [
            {
                "relationship": {"id": "REL-1"},
                "parent": {"id": "PARENT-1"},
                "child": {"id": "ITEM-1"},
                "parent_number": "ASM-001",
                "parent_name": "Assembly",
                "child_number": "P-001",
                "child_name": "Part",
                "level": 1,
            }
        ]
        response = client.get("/api/v1/bom/ITEM-1/where-used?recursive=true&max_levels=4")

    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == "ITEM-1"
    assert body["count"] == 1
    assert body["recursive"] is True
    assert body["max_levels"] == 4
    assert body["parents"][0]["line"] == {}
    assert body["parents"][0]["line_normalized"] == {}
    mock_service.return_value.get_where_used.assert_called_once_with(
        item_id="ITEM-1",
        recursive=True,
        max_levels=4,
    )


def test_where_used_schema_permission_denied_returns_403(client):
    with patch(
        "yuantus.meta_engine.web.bom_where_used_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.get("/api/v1/bom/where-used/schema")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_where_used_schema_success_returns_line_schema(client):
    with patch(
        "yuantus.meta_engine.web.bom_where_used_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_where_used_router.BOMService.line_schema"
    ) as mock_line_schema:
        mock_perm.return_value.check_permission.return_value = True
        mock_line_schema.return_value = [
            {
                "field": "uom",
                "severity": "info",
                "normalized": "EA",
                "description": "Unit of measure",
            }
        ]
        response = client.get("/api/v1/bom/where-used/schema")
    assert response.status_code == 200
    assert response.json() == {
        "line_fields": [
            {
                "field": "uom",
                "severity": "info",
                "normalized": "EA",
                "description": "Unit of measure",
            }
        ]
    }

