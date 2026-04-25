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


def test_merge_branch_uses_dependency_user_id_not_body_user_id():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_lifecycle_router.VersionService") as service_cls:
        service_cls.return_value.merge_branch.return_value = SimpleNamespace(
            id="ver-merged",
            item_id="item-1",
        )
        resp = client.post(
            "/api/v1/versions/items/item-1/merge",
            json={
                "source_version_id": "ver-branch",
                "target_version_id": "ver-main",
                "user_id": 99,
            },
        )

    assert resp.status_code == 200
    service_cls.return_value.merge_branch.assert_called_once_with(
        "item-1",
        "ver-branch",
        "ver-main",
        7,
    )
    assert db.commit.called


def test_merge_branch_maps_lock_conflict_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_lifecycle_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.merge_branch.side_effect = VersionError(
            "Target version ver-main is not checked out by you"
        )
        resp = client.post(
            "/api/v1/versions/items/item-1/merge",
            json={
                "source_version_id": "ver-branch",
                "target_version_id": "ver-main",
            },
        )

    assert resp.status_code == 409
    assert "not checked out by you" in resp.json()["detail"]
    assert db.rollback.called


def test_merge_branch_maps_missing_versions_to_404():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_lifecycle_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.merge_branch.side_effect = VersionError(
            "Source or Target version not found"
        )
        resp = client.post(
            "/api/v1/versions/items/item-1/merge",
            json={
                "source_version_id": "ver-branch",
                "target_version_id": "ver-main",
            },
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source or Target version not found"
    assert db.rollback.called
