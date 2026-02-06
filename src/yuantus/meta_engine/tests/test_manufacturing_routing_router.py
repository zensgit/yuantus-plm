from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db


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


def test_add_operation_returns_400_for_inactive_workcenter():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=True)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.add_operation.side_effect = ValueError(
            "WorkCenter is inactive: WC-01"
        )
        response = client.post(
            "/api/v1/routings/routing-1/operations",
            json={
                "operation_number": "10",
                "name": "Cut",
                "workcenter_code": "WC-01",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "WorkCenter is inactive: WC-01"
    assert db.rollback.called


def test_add_operation_response_includes_workcenter_fields():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=True)
    client, db = _client_with_user(user)

    op = SimpleNamespace(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut",
        operation_type="fabrication",
        sequence=10,
        workcenter_id="wc-1",
        workcenter_code="WC-01",
        setup_time=1.0,
        run_time=2.0,
        labor_setup_time=1.0,
        labor_run_time=2.0,
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.add_operation.return_value = op
        response = client.post(
            "/api/v1/routings/routing-1/operations",
            json={
                "operation_number": "10",
                "name": "Cut",
                "workcenter_id": "wc-1",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "op-1"
    assert body["workcenter_id"] == "wc-1"
    assert body["workcenter_code"] == "WC-01"
    assert db.commit.called
