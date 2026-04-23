"""
Direct route behavior tests for bom_tree_router (BOM R2 slice).

Covers the 5 endpoints moved out of bom_router.py by R2:
  - GET  /api/v1/bom/{item_id}/effective
  - GET  /api/v1/bom/version/{version_id}
  - POST /api/v1/bom/convert/ebom-to-mbom
  - GET  /api/v1/bom/{parent_id}/tree
  - GET  /api/v1/bom/mbom/{parent_id}/tree

Required by DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_R2 §4.5. Before
R2 the legacy router had no focused route-level test file for these handlers
(no test_bom_tree_effectivity_router.py, no test_bom_ebom_to_mbom_router.py).
This file adds behavior coverage for parameter forwarding, permission
branches, ValueError->404/400 mapping, DB rollback on convert failure, MBOM
Manufacturing Part type guard, and the `_parse_config_selection` JSON guard
that R2 co-migrated.

Uses the isolated-router test pattern (FastAPI + include_router) so the
AuthEnforcementMiddleware is not in the stack -- no AUTH_MODE=optional
fixture needed.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.bom_tree_router import bom_tree_router


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
    app.include_router(bom_tree_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/bom/{item_id}/effective
# ---------------------------------------------------------------------------


def test_effective_item_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.get("/api/v1/bom/MISSING/effective")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item MISSING not found"


def test_effective_permission_denied_returns_403(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.get("/api/v1/bom/ITEM-1/effective")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_effective_forwards_parameters_to_service(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.get_bom_structure.return_value = {"root": "ITEM-1", "children": []}
        response = client.get(
            "/api/v1/bom/ITEM-1/effective"
            "?date=2026-04-01T00:00:00"
            "&levels=5"
            "&lot_number=LOT42"
            "&serial_number=SN7"
            "&unit_position=UP3"
            '&config={"region":"EU"}'
        )
    assert response.status_code == 200
    assert response.json()["root"] == "ITEM-1"
    called_args = mock_service.return_value.get_bom_structure.call_args
    assert called_args.args == ("ITEM-1",)
    kwargs = called_args.kwargs
    assert kwargs["levels"] == 5
    assert kwargs["lot_number"] == "LOT42"
    assert kwargs["serial_number"] == "SN7"
    assert kwargs["unit_position"] == "UP3"
    assert kwargs["config_selection"] == {"region": "EU"}
    # effective_date must be the parsed datetime, not None
    assert kwargs["effective_date"] is not None
    assert kwargs["effective_date"].year == 2026


# ---------------------------------------------------------------------------
# GET /api/v1/bom/version/{version_id}
# ---------------------------------------------------------------------------


def test_version_service_call_success(client, mock_db_session):
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMService"
    ) as mock_service:
        mock_service.return_value.get_bom_for_version.return_value = {
            "version_id": "V-123",
            "rows": [],
        }
        response = client.get("/api/v1/bom/version/V-123?levels=7")
    assert response.status_code == 200
    assert response.json()["version_id"] == "V-123"
    mock_service.return_value.get_bom_for_version.assert_called_once_with("V-123", levels=7)


def test_version_value_error_maps_to_404(client, mock_db_session):
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMService"
    ) as mock_service:
        mock_service.return_value.get_bom_for_version.side_effect = ValueError("unknown version")
        response = client.get("/api/v1/bom/version/V-XXX")
    assert response.status_code == 404
    assert response.json()["detail"] == "unknown version"


# ---------------------------------------------------------------------------
# POST /api/v1/bom/convert/ebom-to-mbom
# ---------------------------------------------------------------------------


def test_convert_root_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.post(
        "/api/v1/bom/convert/ebom-to-mbom",
        json={"root_id": "NOPE"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Item NOPE not found"


def test_convert_non_part_root_returns_400(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Document"
    mock_db_session.get.return_value = root
    response = client.post(
        "/api/v1/bom/convert/ebom-to-mbom",
        json={"root_id": "DOC-1"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only Part EBOM can be converted"


def test_convert_permission_denied_returns_403(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Part"
    mock_db_session.get.return_value = root
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.side_effect = [True, False]
        response = client.post(
            "/api/v1/bom/convert/ebom-to-mbom",
            json={"root_id": "PART-1"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_convert_success_returns_mbom_identifiers(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Part"
    mock_db_session.get.return_value = root
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMConversionService"
    ) as mock_conv:
        mock_perm.return_value.check_permission.return_value = True
        mbom_root = MagicMock()
        mbom_root.id = "MBOM-1"
        mbom_root.item_type_id = "Manufacturing Part"
        mbom_root.config_id = "CFG-1"
        mock_conv.return_value.convert_ebom_to_mbom.return_value = mbom_root
        response = client.post(
            "/api/v1/bom/convert/ebom-to-mbom",
            json={"root_id": "PART-1"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["source_root_id"] == "PART-1"
    assert body["mbom_root_id"] == "MBOM-1"
    assert body["mbom_root_type"] == "Manufacturing Part"
    assert body["mbom_root_config_id"] == "CFG-1"
    mock_conv.return_value.convert_ebom_to_mbom.assert_called_once_with("PART-1", user_id=1)


def test_convert_value_error_rollbacks_and_returns_400(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Part"
    mock_db_session.get.return_value = root
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMConversionService"
    ) as mock_conv:
        mock_perm.return_value.check_permission.return_value = True
        mock_conv.return_value.convert_ebom_to_mbom.side_effect = ValueError("cycle or bad EBOM")
        response = client.post(
            "/api/v1/bom/convert/ebom-to-mbom",
            json={"root_id": "PART-1"},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "cycle or bad EBOM"
    assert mock_db_session.rollback.called


# ---------------------------------------------------------------------------
# GET /api/v1/bom/{parent_id}/tree
# ---------------------------------------------------------------------------


def test_tree_forwards_depth_effectivity_and_config(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Part"
    mock_db_session.get.return_value = root
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.get_tree.return_value = {"parent_id": "PART-1"}
        response = client.get(
            "/api/v1/bom/PART-1/tree"
            "?depth=-1"
            "&effective_date=2026-04-01T00:00:00"
            "&lot_number=LOT9"
            "&serial_number=SN9"
            "&unit_position=UP9"
            '&config={"rev":"B"}'
        )
    assert response.status_code == 200
    called = mock_service.return_value.get_tree.call_args
    assert called.args == ("PART-1",)
    kwargs = called.kwargs
    assert kwargs["depth"] == -1
    assert kwargs["lot_number"] == "LOT9"
    assert kwargs["serial_number"] == "SN9"
    assert kwargs["unit_position"] == "UP9"
    assert kwargs["config_selection"] == {"rev": "B"}
    assert kwargs["effective_date"] is not None
    assert "relationship_types" not in kwargs


def test_tree_invalid_config_json_returns_400(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Part"
    mock_db_session.get.return_value = root
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = True
        response = client.get("/api/v1/bom/PART-1/tree?config=not-a-json")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid config JSON"


# ---------------------------------------------------------------------------
# GET /api/v1/bom/mbom/{parent_id}/tree
# ---------------------------------------------------------------------------


def test_mbom_tree_rejects_non_manufacturing_part(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Part"
    mock_db_session.get.return_value = root
    response = client.get("/api/v1/bom/mbom/PART-1/tree")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Manufacturing Part ID"


def test_mbom_tree_forwards_manufacturing_bom_relationship_types(client, mock_db_session):
    root = MagicMock()
    root.item_type_id = "Manufacturing Part"
    mock_db_session.get.return_value = root
    with patch(
        "yuantus.meta_engine.web.bom_tree_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_tree_router.BOMService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.get_tree.return_value = {"parent_id": "MP-1"}
        response = client.get("/api/v1/bom/mbom/MP-1/tree?depth=3")
    assert response.status_code == 200
    called = mock_service.return_value.get_tree.call_args
    assert called.args == ("MP-1",)
    kwargs = called.kwargs
    assert kwargs["depth"] == 3
    assert kwargs["relationship_types"] == ["Manufacturing BOM"]
