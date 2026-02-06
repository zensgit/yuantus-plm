from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.manufacturing.models import WorkCenter


def _client_with_user(user):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), mock_db_session


def test_create_workcenter_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.post(
        "/api/v1/workcenters",
        json={"code": "WC-SEC", "name": "Secure Cell"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_update_workcenter_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.patch(
        "/api/v1/workcenters/wc-1",
        json={"name": "No Access"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_create_workcenter_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    workcenter = WorkCenter(id="wc-1", code="WC-SEC", name="Secure Cell", is_active=True)

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.WorkCenterService"
    ) as service_cls:
        service_cls.return_value.create_workcenter.return_value = workcenter
        response = client.post(
            "/api/v1/workcenters",
            json={"code": "WC-SEC", "name": "Secure Cell"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "wc-1"
    assert body["code"] == "WC-SEC"
    assert body["name"] == "Secure Cell"
    assert body["is_active"] is True
    assert db.commit.called
