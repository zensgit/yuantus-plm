"""Tests for C5/C9 – Maintenance router integration."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.web.maintenance_category_router import maintenance_category_router
from yuantus.meta_engine.web.maintenance_equipment_router import maintenance_equipment_router
from yuantus.meta_engine.web.maintenance_request_router import maintenance_request_router
from yuantus.meta_engine.web.maintenance_router import maintenance_router
from yuantus.meta_engine.web.maintenance_schedule_router import maintenance_schedule_router


def _client_with_db():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(maintenance_category_router, prefix="/api/v1")
    app.include_router(maintenance_equipment_router, prefix="/api/v1")
    app.include_router(maintenance_request_router, prefix="/api/v1")
    app.include_router(maintenance_schedule_router, prefix="/api/v1")
    app.include_router(maintenance_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = lambda: None
    return TestClient(app), mock_db_session


# ============================================================================
# C5 – baseline router tests
# ============================================================================


def test_maintenance_category_and_equipment_endpoints_commit():
    client, db = _client_with_db()

    with (
        patch("yuantus.meta_engine.web.maintenance_category_router.MaintenanceService") as category_service_cls,
        patch("yuantus.meta_engine.web.maintenance_equipment_router.MaintenanceService") as equipment_service_cls,
    ):
        service = MagicMock()
        category_service_cls.return_value = service
        equipment_service_cls.return_value = service
        service.create_category.return_value = SimpleNamespace(
            id="cat-1",
            name="CNC Machines",
            parent_id=None,
            description=None,
            created_at=None,
        )
        service.list_categories.return_value = [service.create_category.return_value]
        service.create_equipment.return_value = SimpleNamespace(
            id="eq-1",
            name="CNC Mill #3",
            serial_number="SN-3",
            model="VF-2",
            manufacturer="Haas",
            category_id="cat-1",
            status="operational",
            location="Plant 1",
            plant_code="PLT-1",
            workcenter_id="wc-1",
            team_name="Maintenance",
            expected_mtbf_days=180.0,
            created_at=None,
        )
        service.list_equipment.return_value = [service.create_equipment.return_value]

        create_category = client.post("/api/v1/maintenance/categories", json={"name": "CNC Machines"})
        list_categories = client.get("/api/v1/maintenance/categories")
        create_equipment = client.post(
            "/api/v1/maintenance/equipment",
            json={"name": "CNC Mill #3", "category_id": "cat-1", "plant_code": "PLT-1"},
        )
        list_equipment = client.get("/api/v1/maintenance/equipment")

    assert create_category.status_code == 200
    assert list_categories.status_code == 200
    assert list_categories.json()["total"] == 1
    assert create_equipment.status_code == 200
    assert list_equipment.status_code == 200
    assert list_equipment.json()["equipment"][0]["id"] == "eq-1"
    assert db.commit.call_count == 2


def test_maintenance_request_transition_endpoints_return_service_payloads():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.maintenance_request_router.MaintenanceService") as service_cls:
        service = service_cls.return_value
        service.create_request.return_value = SimpleNamespace(
            id="mr-1",
            name="Fix spindle vibration",
            equipment_id="eq-1",
            maintenance_type="corrective",
            state="draft",
            priority="high",
            description="Excessive vibration",
            resolution_note=None,
            scheduled_date=None,
            due_date=None,
            duration_hours=None,
            team_name="Maintenance",
            assigned_user_id=1,
            created_at=None,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
        )
        transitioned_request_payload = dict(service.create_request.return_value.__dict__)
        transitioned_request_payload["state"] = "in_progress"
        service.transition_request.return_value = SimpleNamespace(
            **transitioned_request_payload
        )

        create_response = client.post(
            "/api/v1/maintenance/requests",
            json={
                "name": "Fix spindle vibration",
                "equipment_id": "eq-1",
                "maintenance_type": "corrective",
                "priority": "high",
            },
        )
        transition_response = client.post(
            "/api/v1/maintenance/requests/mr-1/transition",
            json={"target_state": "in_progress"},
        )

    assert create_response.status_code == 200
    assert create_response.json()["state"] == "draft"
    assert transition_response.status_code == 200
    assert transition_response.json()["state"] == "in_progress"
    assert db.commit.call_count == 2


# ============================================================================
# C9 – Readiness, Preventive Schedule, Queue Summary router tests
# ============================================================================


def test_equipment_readiness_summary_endpoint():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.maintenance_equipment_router.MaintenanceService") as svc_cls:
        service = svc_cls.return_value
        service.get_equipment_readiness_summary.return_value = {
            "total_equipment": 5,
            "operational": 4,
            "readiness_pct": 80.0,
            "status_counts": {"operational": 4, "in_maintenance": 1},
            "needs_attention": [
                {"equipment_id": "eq-3", "name": "Lathe DOWN", "status": "in_maintenance",
                 "workcenter_id": "wc-1", "plant_code": "PLT-A"},
            ],
            "filters": {"plant_code": "PLT-A", "workcenter_id": None},
        }

        response = client.get(
            "/api/v1/maintenance/equipment/readiness-summary",
            params={"plant_code": "PLT-A"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_equipment"] == 5
    assert data["readiness_pct"] == 80.0
    assert len(data["needs_attention"]) == 1
    service.get_equipment_readiness_summary.assert_called_once_with(
        plant_code="PLT-A", workcenter_id=None,
    )


def test_readiness_summary_route_not_shadowed_by_equipment_id():
    """Verify /equipment/readiness-summary is matched before /equipment/{id}."""
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.maintenance_equipment_router.MaintenanceService") as svc_cls:
        service = svc_cls.return_value
        service.get_equipment_readiness_summary.return_value = {
            "total_equipment": 0, "operational": 0, "readiness_pct": 0.0,
            "status_counts": {}, "needs_attention": [],
            "filters": {"plant_code": None, "workcenter_id": None},
        }

        response = client.get("/api/v1/maintenance/equipment/readiness-summary")

    assert response.status_code == 200
    assert "total_equipment" in response.json()
    service.get_equipment.assert_not_called()


def test_preventive_schedule_endpoint():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.maintenance_schedule_router.MaintenanceService") as svc_cls:
        service = svc_cls.return_value
        service.get_preventive_schedule.return_value = {
            "reference_date": "2026-03-18T00:00:00",
            "window_days": 14,
            "overdue": [
                {"request_id": "mr-1", "name": "PM Oil Change", "days_overdue": 30,
                 "equipment_id": "eq-1", "state": "submitted", "priority": "medium",
                 "due_date": "2026-02-16T00:00:00", "scheduled_date": None},
            ],
            "overdue_count": 1,
            "upcoming": [],
            "upcoming_count": 0,
        }

        response = client.get(
            "/api/v1/maintenance/preventive-schedule",
            params={"window_days": 14},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["overdue_count"] == 1
    assert data["overdue"][0]["days_overdue"] == 30
    service.get_preventive_schedule.assert_called_once_with(
        window_days=14, include_overdue=True,
    )


def test_queue_summary_endpoint():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.maintenance_schedule_router.MaintenanceService") as svc_cls:
        service = svc_cls.return_value
        service.get_maintenance_queue_summary.return_value = {
            "total_active": 3,
            "by_priority": {"high": 1, "medium": 2},
            "by_type": {"corrective": 2, "preventive": 1},
            "by_state": {"draft": 1, "submitted": 2},
            "queue": [
                {"request_id": "mr-1", "name": "Urgent fix", "equipment_id": "eq-1",
                 "maintenance_type": "corrective", "state": "submitted", "priority": "high",
                 "due_date": None, "scheduled_date": None, "team_name": "Team A",
                 "duration_hours": 4.0},
            ],
            "filters": {"plant_code": None, "workcenter_id": "wc-2"},
        }

        response = client.get(
            "/api/v1/maintenance/queue-summary",
            params={"workcenter_id": "wc-2"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_active"] == 3
    assert data["by_priority"]["high"] == 1
    service.get_maintenance_queue_summary.assert_called_once_with(
        plant_code=None, workcenter_id="wc-2",
    )


def test_equipment_404_still_works():
    """Ensure the path param route still returns 404 for missing equipment."""
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.maintenance_equipment_router.MaintenanceService") as svc_cls:
        service = svc_cls.return_value
        service.get_equipment.return_value = None

        response = client.get("/api/v1/maintenance/equipment/no-such")

    assert response.status_code == 404


def test_maintenance_routes_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/maintenance/categories" in paths
    assert "/api/v1/maintenance/equipment/readiness-summary" in paths
    assert "/api/v1/maintenance/preventive-schedule" in paths
    assert "/api/v1/maintenance/queue-summary" in paths
