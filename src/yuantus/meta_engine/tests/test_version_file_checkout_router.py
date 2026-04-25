from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    """These tests override route auth dependency; middleware auth is out of scope."""
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


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


def test_version_file_checkout_routes_registered_in_create_app():
    app = create_app()
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes}

    assert ("/api/v1/versions/{version_id}/files/{file_id}/checkout", ("POST",)) in paths
    assert (
        "/api/v1/versions/{version_id}/files/{file_id}/undo-checkout",
        ("POST",),
    ) in paths
    assert ("/api/v1/versions/{version_id}/files/{file_id}/lock", ("GET",)) in paths


def test_version_file_checkout_returns_200_and_commits():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        service_cls.return_value.checkout_file.return_value = SimpleNamespace(
            id="vf-1",
            version_id="ver-1",
            file_id="file-1",
            file_role="preview",
            checked_out_by_id=7,
            checked_out_at=datetime(2026, 4, 15, 12, 0, 0),
        )
        resp = client.post(
            "/api/v1/versions/ver-1/files/file-1/checkout",
            params={"file_role": "preview"},
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "id": "vf-1",
        "version_id": "ver-1",
        "file_id": "file-1",
        "file_role": "preview",
        "checked_out_by_id": 7,
        "checked_out_at": "2026-04-15T12:00:00",
    }
    service_cls.return_value.checkout_file.assert_called_once_with(
        "ver-1",
        "file-1",
        7,
        file_role="preview",
    )
    assert db.commit.called


def test_version_file_checkout_maps_missing_targets_to_404():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        from yuantus.meta_engine.version.file_service import VersionFileError

        service_cls.return_value.checkout_file.side_effect = VersionFileError(
            "Version ver-1 not found"
        )
        resp = client.post("/api/v1/versions/ver-1/files/file-1/checkout")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Version ver-1 not found"
    assert db.rollback.called


def test_version_file_checkout_maps_locked_or_released_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        from yuantus.meta_engine.version.file_service import VersionFileError

        service_cls.return_value.checkout_file.side_effect = VersionFileError(
            "File file-1 is already checked out by user 9"
        )
        resp = client.post("/api/v1/versions/ver-1/files/file-1/checkout")

    assert resp.status_code == 409
    assert "already checked out" in resp.json()["detail"]
    assert db.rollback.called


def test_version_file_lock_endpoint_returns_lock_payload():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        service_cls.return_value.get_file_lock.return_value = {
            "id": "vf-1",
            "version_id": "ver-1",
            "file_id": "file-1",
            "file_role": "preview",
            "checked_out_by_id": 7,
            "checked_out_at": "2026-04-15T12:00:00",
        }
        resp = client.get(
            "/api/v1/versions/ver-1/files/file-1/lock",
            params={"file_role": "preview"},
        )

    assert resp.status_code == 200
    assert resp.json()["checked_out_by_id"] == 7
    service_cls.return_value.get_file_lock.assert_called_once_with(
        "ver-1",
        "file-1",
        file_role="preview",
    )


def test_version_file_undo_checkout_returns_200_and_commits():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        service_cls.return_value.undo_checkout_file.return_value = SimpleNamespace(
            id="vf-1",
            version_id="ver-1",
            file_id="file-1",
            file_role="preview",
            checked_out_by_id=None,
            checked_out_at=None,
        )
        resp = client.post(
            "/api/v1/versions/ver-1/files/file-1/undo-checkout",
            params={"file_role": "preview"},
        )

    assert resp.status_code == 200
    assert resp.json()["checked_out_by_id"] is None
    service_cls.return_value.undo_checkout_file.assert_called_once_with(
        "ver-1",
        "file-1",
        7,
        file_role="preview",
    )
    assert db.commit.called


def test_attach_file_maps_foreign_file_lock_to_409():
    client, db = _client_with_user_id(7)
    db.get.return_value = SimpleNamespace(
        id="ver-1",
        is_released=False,
        checked_out_by_id=7,
    )

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        from yuantus.meta_engine.version.file_service import VersionFileError

        service_cls.return_value.attach_file.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.post(
            "/api/v1/versions/ver-1/files",
            json={
                "file_id": "file-1",
                "file_role": "preview",
                "is_primary": False,
                "sequence": 0,
            },
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    service_cls.return_value.attach_file.assert_called_once_with(
        version_id="ver-1",
        file_id="file-1",
        file_role="preview",
        is_primary=False,
        sequence=0,
        user_id=7,
    )
    assert db.rollback.called


def test_detach_file_maps_foreign_file_lock_to_409():
    client, db = _client_with_user_id(7)
    db.get.return_value = SimpleNamespace(
        id="ver-1",
        is_released=False,
        checked_out_by_id=7,
    )

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        from yuantus.meta_engine.version.file_service import VersionFileError

        service_cls.return_value.detach_file.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.delete(
            "/api/v1/versions/ver-1/files/file-1",
            params={"file_role": "preview"},
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    service_cls.return_value.detach_file.assert_called_once_with(
        "ver-1",
        "file-1",
        "preview",
        user_id=7,
    )
    assert db.rollback.called


def test_set_primary_maps_foreign_file_lock_to_409():
    client, db = _client_with_user_id(7)
    db.get.return_value = SimpleNamespace(
        id="ver-1",
        is_released=False,
        checked_out_by_id=7,
    )

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        from yuantus.meta_engine.version.file_service import VersionFileError

        service_cls.return_value.set_primary_file.side_effect = VersionFileError(
            "File file-2 is checked out by another user"
        )
        resp = client.put(
            "/api/v1/versions/ver-1/files/primary",
            json={"file_id": "file-2", "file_role": "preview"},
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    service_cls.return_value.set_primary_file.assert_called_once_with(
        "ver-1",
        "file-2",
        user_id=7,
        file_role="preview",
    )
    assert db.rollback.called


def test_version_detail_route_uses_file_router_service():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        service_cls.return_value.get_version_detail.return_value = {
            "id": "ver-1",
            "files": [{"file_id": "file-1"}],
        }
        resp = client.get("/api/v1/versions/ver-1/detail")

    assert resp.status_code == 200
    assert resp.json()["files"] == [{"file_id": "file-1"}]
    service_cls.return_value.get_version_detail.assert_called_once_with("ver-1")


def test_version_thumbnail_route_sets_thumbnail_and_commits():
    client, db = _client_with_user_id(7)
    db.get.return_value = SimpleNamespace(
        id="ver-1",
        is_released=False,
        checked_out_by_id=7,
    )

    with patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as service_cls:
        service_cls.return_value.set_thumbnail.return_value = SimpleNamespace(id="ver-1")
        resp = client.put(
            "/api/v1/versions/ver-1/thumbnail",
            json={"thumbnail_data": "base64-data"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": "updated", "version_id": "ver-1"}
    service_cls.return_value.set_thumbnail.assert_called_once_with(
        "ver-1",
        "base64-data",
    )
    assert db.commit.called


def test_compare_full_route_combines_property_and_file_diffs():
    client, _db = _client_with_user_id(7)

    with (
        patch("yuantus.meta_engine.web.version_file_router.VersionService") as version_cls,
        patch("yuantus.meta_engine.web.version_file_router.VersionFileService") as file_cls,
    ):
        version_cls.return_value.compare_versions.return_value = {"properties": []}
        file_cls.return_value.compare_version_files.return_value = {"files": []}
        resp = client.get("/api/v1/versions/compare-full", params={"v1": "v1", "v2": "v2"})

    assert resp.status_code == 200
    assert resp.json() == {
        "property_comparison": {"properties": []},
        "file_comparison": {"files": []},
    }
    version_cls.return_value.compare_versions.assert_called_once_with("v1", "v2")
    file_cls.return_value.compare_version_files.assert_called_once_with("v1", "v2")


def test_tree_full_route_enriches_version_file_metadata():
    client, db = _client_with_user_id(7)
    version = SimpleNamespace(
        file_count=2,
        thumbnail_data="thumb",
        primary_file_id="file-primary",
    )
    db.get.side_effect = [version, None]

    with patch("yuantus.meta_engine.web.version_file_router.VersionService") as version_cls:
        version_cls.return_value.get_version_tree.return_value = [
            {"id": "ver-1"},
            {"id": "ver-2"},
        ]
        resp = client.get("/api/v1/versions/items/item-1/tree-full")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": "ver-1",
            "file_count": 2,
            "thumbnail": "thumb",
            "primary_file_id": "file-primary",
        },
        {"id": "ver-2"},
    ]
    version_cls.return_value.get_version_tree.assert_called_once_with("item-1")
