"""Tests for C4/C8 – Quality router integration."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.web.quality_router import quality_router


def _client_with_db():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(quality_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = lambda: None
    return TestClient(app), mock_db_session


# ============================================================================
# C4 – baseline router tests
# ============================================================================


def test_quality_point_endpoints_commit_and_return_service_payloads():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.create_point.return_value = SimpleNamespace(
            id="qp-1",
            name="Visual Inspection",
            check_type="pass_fail",
            product_id="item-1",
            item_type_id=None,
            routing_id=None,
            operation_id=None,
            trigger_on="manual",
            measure_min=None,
            measure_max=None,
            measure_unit=None,
            is_active=True,
            sequence=10,
            team_name="QA",
            created_at=None,
        )
        service.list_points.return_value = [service.create_point.return_value]
        updated_point_payload = dict(service.create_point.return_value.__dict__)
        updated_point_payload["is_active"] = False
        service.update_point.return_value = SimpleNamespace(**updated_point_payload)

        create_response = client.post(
            "/api/v1/quality/points",
            json={"name": "Visual Inspection", "team_name": "QA"},
        )
        list_response = client.get("/api/v1/quality/points")
        update_response = client.patch(
            "/api/v1/quality/points/qp-1",
            json={"is_active": False},
        )

    assert create_response.status_code == 200
    assert create_response.json()["id"] == "qp-1"
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False
    assert db.commit.call_count == 2


def test_quality_check_and_alert_endpoints_use_router_contracts():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.create_check.return_value = SimpleNamespace(
            id="qc-1",
            point_id="qp-1",
            product_id="item-1",
            routing_id="routing-1",
            operation_id="op-10",
            check_type="measure",
            result="none",
            measure_value=None,
            note=None,
            source_document_ref="MO-1",
            lot_serial="LOT-1",
            checked_at=None,
            checked_by_id=None,
            created_at=None,
        )
        recorded_check_payload = dict(service.create_check.return_value.__dict__)
        recorded_check_payload.update(
            {"result": "pass", "measure_value": 10.0, "note": "within range"}
        )
        service.record_check_result.return_value = SimpleNamespace(**recorded_check_payload)
        service.create_alert.return_value = SimpleNamespace(
            id="qa-1",
            name="Out of tolerance",
            check_id="qc-1",
            product_id="item-1",
            state="new",
            priority="high",
            description="Diameter drift",
            root_cause=None,
            corrective_action=None,
            team_name="QA",
            assigned_user_id=None,
            created_at=None,
            confirmed_at=None,
            resolved_at=None,
            closed_at=None,
        )
        transitioned_alert_payload = dict(service.create_alert.return_value.__dict__)
        transitioned_alert_payload["state"] = "confirmed"
        service.transition_alert.return_value = SimpleNamespace(**transitioned_alert_payload)

        check_response = client.post(
            "/api/v1/quality/checks",
            json={"point_id": "qp-1", "product_id": "item-1"},
        )
        record_response = client.post(
            "/api/v1/quality/checks/qc-1/record",
            json={"result": "pass", "measure_value": 10.0, "note": "within range"},
        )
        alert_response = client.post(
            "/api/v1/quality/alerts",
            json={"name": "Out of tolerance", "check_id": "qc-1", "priority": "high"},
        )
        transition_response = client.post(
            "/api/v1/quality/alerts/qa-1/transition",
            json={"target_state": "confirmed"},
        )

    assert check_response.status_code == 200
    assert check_response.json()["routing_id"] == "routing-1"
    assert check_response.json()["operation_id"] == "op-10"
    assert record_response.status_code == 200
    assert record_response.json()["result"] == "pass"
    assert alert_response.status_code == 200
    assert alert_response.json()["state"] == "new"
    assert transition_response.status_code == 200
    assert transition_response.json()["state"] == "confirmed"
    assert db.commit.call_count == 4


# ============================================================================
# C8 – routing/operation filter & manufacturing context router tests
# ============================================================================


def test_list_points_passes_routing_and_operation_filters():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.list_points.return_value = []

        response = client.get(
            "/api/v1/quality/points",
            params={"routing_id": "r-1", "operation_id": "op-5"},
        )

    assert response.status_code == 200
    service.list_points.assert_called_once_with(
        product_id=None,
        item_type_id=None,
        routing_id="r-1",
        operation_id="op-5",
        check_type=None,
        is_active=None,
    )


def test_list_checks_passes_routing_and_operation_filters():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.list_checks.return_value = []

        response = client.get(
            "/api/v1/quality/checks",
            params={"routing_id": "r-2", "operation_id": "op-10"},
        )

    assert response.status_code == 200
    service.list_checks.assert_called_once_with(
        point_id=None,
        product_id=None,
        routing_id="r-2",
        operation_id="op-10",
        result=None,
    )


def test_create_point_with_routing_id():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.create_point.return_value = SimpleNamespace(
            id="qp-2",
            name="Assembly Check",
            check_type="pass_fail",
            product_id=None,
            item_type_id=None,
            routing_id="routing-1",
            operation_id="op-20",
            trigger_on="production",
            measure_min=None,
            measure_max=None,
            measure_unit=None,
            is_active=True,
            sequence=10,
            team_name=None,
            created_at=None,
        )

        response = client.post(
            "/api/v1/quality/points",
            json={
                "name": "Assembly Check",
                "routing_id": "routing-1",
                "operation_id": "op-20",
                "trigger_on": "production",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["routing_id"] == "routing-1"
    assert data["operation_id"] == "op-20"
    service.create_point.assert_called_once()
    call_kwargs = service.create_point.call_args[1]
    assert call_kwargs["routing_id"] == "routing-1"
    assert call_kwargs["operation_id"] == "op-20"


def test_alert_manufacturing_context_endpoint():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.get_alert_manufacturing_context.return_value = {
            "alert_id": "qa-1",
            "alert_name": "Torque failure",
            "alert_state": "new",
            "alert_priority": "high",
            "product_id": "item-1",
            "check": {
                "check_id": "qc-1",
                "check_type": "measure",
                "result": "fail",
                "measure_value": 25.0,
                "source_document_ref": "MO-200",
                "lot_serial": "LOT-A",
            },
            "point": {
                "point_id": "qp-1",
                "point_name": "Torque Check",
                "routing_id": "routing-1",
                "operation_id": "op-30",
                "trigger_on": "production",
                "measure_min": 10.0,
                "measure_max": 20.0,
                "measure_unit": "Nm",
            },
            "manufacturing_summary": {
                "routing_id": "routing-1",
                "operation_id": "op-30",
                "source_document_ref": "MO-200",
                "product_id": "item-1",
                "lot_serial": "LOT-A",
            },
        }

        response = client.get("/api/v1/quality/alerts/qa-1/manufacturing-context")

    assert response.status_code == 200
    data = response.json()
    assert data["alert_id"] == "qa-1"
    assert data["manufacturing_summary"]["routing_id"] == "routing-1"
    assert data["check"]["result"] == "fail"
    assert data["point"]["measure_unit"] == "Nm"


def test_alert_manufacturing_context_404_when_not_found():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_router.QualityService") as service_cls:
        service = service_cls.return_value
        service.get_alert_manufacturing_context.return_value = None

        response = client.get(
            "/api/v1/quality/alerts/no-such/manufacturing-context"
        )

    assert response.status_code == 404
