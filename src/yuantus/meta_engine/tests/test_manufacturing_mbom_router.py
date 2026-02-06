from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.manufacturing.models import ManufacturingBOM


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


def test_release_mbom_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.put("/api/v1/mboms/mbom-1/release")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_release_mbom_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    mbom = ManufacturingBOM(
        id="mbom-1",
        source_item_id="item-1",
        name="MBOM 1",
        version="1.0",
        state="released",
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.MBOMService"
    ) as service_cls:
        service_cls.return_value.release_mbom.return_value = mbom
        response = client.put("/api/v1/mboms/mbom-1/release")

    assert response.status_code == 200
    assert response.json()["state"] == "released"
    assert db.commit.called


def test_reopen_mbom_not_found_returns_404():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.MBOMService"
    ) as service_cls:
        service_cls.return_value.reopen_mbom.side_effect = ValueError(
            "MBOM not found: mbom-missing"
        )
        response = client.put("/api/v1/mboms/mbom-missing/reopen")

    assert response.status_code == 404
    assert response.json()["detail"] == "MBOM not found: mbom-missing"
    assert db.rollback.called
