from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.manufacturing.models import Routing


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


def test_create_routing_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.post(
        "/api/v1/routings",
        json={
            "name": "Routing",
            "item_id": "part-1",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_add_operation_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.post(
        "/api/v1/routings/routing-1/operations",
        json={
            "operation_number": "10",
            "name": "Cut",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


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


def test_list_operations_returns_items():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)
    operation = SimpleNamespace(
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
        queue_time=0.0,
        move_time=0.0,
        wait_time=0.0,
        labor_setup_time=1.0,
        labor_run_time=2.0,
        crew_size=1,
        machines_required=1,
        is_subcontracted=False,
        inspection_required=False,
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.list_operations.return_value = [operation]
        response = client.get("/api/v1/routings/routing-1/operations")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "op-1"
    assert payload[0]["workcenter_id"] == "wc-1"


def test_update_operation_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    operation = SimpleNamespace(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut Updated",
        operation_type="fabrication",
        sequence=10,
        workcenter_id="wc-1",
        workcenter_code="WC-01",
        setup_time=1.0,
        run_time=3.0,
        queue_time=0.0,
        move_time=0.0,
        wait_time=0.0,
        labor_setup_time=1.0,
        labor_run_time=3.0,
        crew_size=1,
        machines_required=1,
        is_subcontracted=False,
        inspection_required=False,
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.update_operation.return_value = operation
        response = client.patch(
            "/api/v1/routings/routing-1/operations/op-1",
            json={"name": "Cut Updated", "run_time": 3.0},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Cut Updated"
    assert db.commit.called


def test_delete_operation_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        response = client.delete("/api/v1/routings/routing-1/operations/op-1")

    assert response.status_code == 200
    assert response.json() == {"deleted": True, "operation_id": "op-1"}
    assert service_cls.return_value.delete_operation.called
    assert db.commit.called


def test_resequence_operations_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    op1 = SimpleNamespace(
        id="op-2",
        routing_id="routing-1",
        operation_number="20",
        name="Weld",
        operation_type="fabrication",
        sequence=10,
        workcenter_id=None,
        workcenter_code=None,
        setup_time=1.0,
        run_time=1.0,
        queue_time=0.0,
        move_time=0.0,
        wait_time=0.0,
        labor_setup_time=1.0,
        labor_run_time=1.0,
        crew_size=1,
        machines_required=1,
        is_subcontracted=False,
        inspection_required=False,
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.resequence_operations.return_value = [op1]
        response = client.post(
            "/api/v1/routings/routing-1/operations/resequence",
            json={"ordered_operation_ids": ["op-2"], "step": 10},
        )

    assert response.status_code == 200
    assert response.json()[0]["id"] == "op-2"
    assert db.commit.called


def test_list_routings_returns_items():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=True)
    client, _db = _client_with_user(user)
    routing = Routing(
        id="routing-1",
        name="R1",
        item_id="part-1",
        version="1.0",
        is_primary=True,
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.list_routings.return_value = [routing]
        response = client.get("/api/v1/routings?item_id=part-1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "routing-1"
    assert payload[0]["is_primary"] is True


def test_set_primary_routing_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)
    response = client.put("/api/v1/routings/routing-1/primary")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_set_primary_routing_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    routing = Routing(
        id="routing-1",
        name="R1",
        item_id="part-1",
        version="1.0",
        is_primary=True,
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.set_primary_routing.return_value = routing
        response = client.put("/api/v1/routings/routing-1/primary")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "routing-1"
    assert body["is_primary"] is True
    assert db.commit.called


def test_set_primary_routing_not_found_returns_404():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.set_primary_routing.side_effect = ValueError(
            "Routing not found: routing-missing"
        )
        response = client.put("/api/v1/routings/routing-missing/primary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Routing not found: routing-missing"
    assert db.rollback.called


def test_release_routing_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)
    response = client.put("/api/v1/routings/routing-1/release")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_routing_release_diagnostics_requires_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)
    response = client.get("/api/v1/routings/routing-1/release-diagnostics")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_routing_release_diagnostics_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [],
            "warnings": [],
        }
        response = client.get("/api/v1/routings/routing-1/release-diagnostics")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["resource_type"] == "routing"
    assert body["resource_id"] == "routing-1"
    assert body["ruleset_id"] == "default"
    assert body["errors"] == []


def test_release_and_reopen_routing_admin_success():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    released = Routing(
        id="routing-1",
        name="R1",
        item_id="part-1",
        version="1.0",
        is_primary=True,
        state="released",
    )
    draft = Routing(
        id="routing-1",
        name="R1",
        item_id="part-1",
        version="1.0",
        is_primary=True,
        state="draft",
    )

    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.release_routing.return_value = released
        release_resp = client.put("/api/v1/routings/routing-1/release")
        service_cls.return_value.reopen_routing.return_value = draft
        reopen_resp = client.put("/api/v1/routings/routing-1/reopen")

    assert release_resp.status_code == 200
    assert release_resp.json()["state"] == "released"
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["state"] == "draft"
    assert db.commit.called


def test_release_routing_not_found_returns_404():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    with patch(
        "yuantus.meta_engine.web.manufacturing_router.RoutingService"
    ) as service_cls:
        service_cls.return_value.release_routing.side_effect = ValueError(
            "Routing not found: routing-missing"
        )
        response = client.put("/api/v1/routings/routing-missing/release")

    assert response.status_code == 404
    assert response.json()["detail"] == "Routing not found: routing-missing"
    assert db.rollback.called
