from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db


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


def test_checkout_maps_foreign_checkout_conflict_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.checkout.side_effect = VersionError(
            "Version ver-1 is checked out by another user"
        )
        resp = client.post("/api/v1/versions/items/item-1/checkout")

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert db.rollback.called


def test_checkout_maps_file_lock_conflict_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.checkout.side_effect = VersionError(
            "Version has file-level locks held by another user (9)"
        )
        resp = client.post("/api/v1/versions/items/item-1/checkout")

    assert resp.status_code == 409
    assert "file-level locks held by another user" in resp.json()["detail"]
    assert db.rollback.called


def test_checkin_maps_file_lock_conflict_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.checkin.side_effect = VersionError(
            "Version has file-level locks held by another user (9)"
        )
        resp = client.post("/api/v1/versions/items/item-1/checkin")

    assert resp.status_code == 409
    assert "file-level locks held by another user" in resp.json()["detail"]
    assert db.rollback.called


def test_checkin_success_preserves_response_shape():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        service_cls.return_value.checkin.return_value = SimpleNamespace(
            id="ver-2",
            item_id="item-1",
        )
        resp = client.post("/api/v1/versions/items/item-1/checkin")

    assert resp.status_code == 200
    assert resp.json()["id"] == "ver-2"
    assert db.commit.called
