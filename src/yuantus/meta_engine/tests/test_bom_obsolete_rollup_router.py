from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.bom_obsolete_rollup_router import bom_obsolete_rollup_router


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
    app.include_router(bom_obsolete_rollup_router, prefix="/api/v1")
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
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.return_value = True
        with patch(
            "yuantus.meta_engine.web.bom_obsolete_rollup_router.BOMObsoleteService"
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
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.MetaPermissionService"
    ) as mock_perm:
        mock_perm.return_value.check_permission.side_effect = [True, False]
        response = client.post(
            "/api/v1/bom/ROOT/rollup/weight",
            json={"write_back": True},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_obsolete_scan_forwards_relationship_types(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.BOMObsoleteService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.scan.return_value = {
            "root_id": "ROOT",
            "count": 0,
            "entries": [],
        }
        response = client.get(
            "/api/v1/bom/ROOT/obsolete"
            "?recursive=false&levels=3&relationship_types=Part%20BOM,Manufacturing%20BOM"
        )
    assert response.status_code == 200
    mock_service.return_value.scan.assert_called_once_with(
        "ROOT",
        recursive=False,
        max_levels=3,
        relationship_types=["Part BOM", "Manufacturing BOM"],
    )


def test_obsolete_resolve_dry_run_rolls_back(client, mock_db_session):
    mock_db_session.get.return_value = MagicMock()
    with patch(
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.BOMObsoleteService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.resolve.return_value = {
            "ok": True,
            "mode": "update",
            "root_id": "ROOT",
            "summary": {},
            "entries": [],
        }
        response = client.post(
            "/api/v1/bom/ROOT/obsolete/resolve",
            json={"dry_run": True, "relationship_types": ["Part BOM"]},
        )
    assert response.status_code == 200
    mock_db_session.rollback.assert_called_once()
    assert not mock_db_session.commit.called
    mock_service.return_value.resolve.assert_called_once_with(
        "ROOT",
        mode="update",
        recursive=True,
        max_levels=10,
        relationship_types=["Part BOM"],
        dry_run=True,
        user_id=1,
    )


def test_weight_rollup_write_back_commits(client, mock_db_session):
    item = MagicMock()
    item.item_type_id = "Part"
    mock_db_session.get.return_value = item
    with patch(
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.MetaPermissionService"
    ) as mock_perm, patch(
        "yuantus.meta_engine.web.bom_obsolete_rollup_router.BOMRollupService"
    ) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.compute_weight_rollup.return_value = {
            "root_id": "ROOT",
            "total_weight": 12.5,
        }
        response = client.post(
            "/api/v1/bom/ROOT/rollup/weight",
            json={"write_back": True, "levels": 4, "write_back_mode": "overwrite"},
        )
    assert response.status_code == 200
    mock_db_session.commit.assert_called_once()
    mock_service.return_value.compute_weight_rollup.assert_called_once()
    assert mock_service.return_value.compute_weight_rollup.call_args.kwargs["levels"] == 4
    assert (
        mock_service.return_value.compute_weight_rollup.call_args.kwargs["write_back_mode"]
        == "overwrite"
    )
