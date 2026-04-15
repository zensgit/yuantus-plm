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


def test_revise_maps_source_checkout_conflict_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.revise.side_effect = VersionError(
            "Source version ver-1 is checked out by another user"
        )
        resp = client.post("/api/v1/versions/items/item-1/revise")

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert db.rollback.called


def test_create_branch_uses_dependency_user_id_not_body_user_id():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        service_cls.return_value.create_branch.return_value = SimpleNamespace(
            id="ver-branch",
            item_id="item-1",
        )
        resp = client.post(
            "/api/v1/versions/items/item-1/branch",
            json={
                "source_version_id": "ver-1",
                "branch_name": "exp",
                "user_id": 99,
            },
        )

    assert resp.status_code == 200
    service_cls.return_value.create_branch.assert_called_once_with(
        "item-1",
        "ver-1",
        "exp",
        7,
    )
    assert db.commit.called


def test_create_branch_maps_source_checkout_conflict_to_409():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.VersionService") as service_cls:
        from yuantus.meta_engine.version.service import VersionError

        service_cls.return_value.create_branch.side_effect = VersionError(
            "Source version ver-1 is checked out by another user"
        )
        resp = client.post(
            "/api/v1/versions/items/item-1/branch",
            json={
                "source_version_id": "ver-1",
                "branch_name": "exp",
            },
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert db.rollback.called
