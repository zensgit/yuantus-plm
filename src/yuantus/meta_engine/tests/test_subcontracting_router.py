"""Tests for C13 – Subcontracting router integration."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.web.subcontracting_router import subcontracting_router


def _client_with_db():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(subcontracting_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = lambda: None
    return TestClient(app), mock_db_session


def test_order_create_list_and_detail_endpoints_use_service_payloads():
    client, db = _client_with_db()
    payload = {
        "id": "so-1",
        "name": "Outside coating",
        "item_id": "item-1",
        "routing_id": "routing-1",
        "source_operation_id": "op-1",
        "state": "draft",
        "vendor_id": "vendor-1",
        "vendor_name": "Acme",
        "requested_qty": 5.0,
        "issued_qty": 0.0,
        "received_qty": 0.0,
        "open_qty": 5.0,
        "completion_pct": 0.0,
        "timeline_total": 0,
        "operation": {"operation_id": "op-1", "routing_id": "routing-1", "operation_number": "20", "name": "Outside coating", "is_subcontracted": True, "subcontractor_id": "vendor-1"},
    }

    with patch("yuantus.meta_engine.web.subcontracting_router.SubcontractingService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_order.return_value = SimpleNamespace(id="so-1")
        svc.get_order_read_model.return_value = payload
        svc.list_orders.return_value = [SimpleNamespace(id="so-1")]

        create_response = client.post("/api/v1/subcontracting/orders", json={"name": "Outside coating", "requested_qty": 5})
        list_response = client.get("/api/v1/subcontracting/orders", params={"vendor_id": "vendor-1"})
        detail_response = client.get("/api/v1/subcontracting/orders/so-1")

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["operation"]["operation_id"] == "op-1"
    svc.list_orders.assert_called_once_with(state=None, vendor_id="vendor-1", routing_id=None, source_operation_id=None)
    assert db.commit.call_count == 1


def test_assign_vendor_issue_receipt_and_timeline_endpoints():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.subcontracting_router.SubcontractingService") as svc_cls:
        svc = svc_cls.return_value
        svc.assign_vendor.return_value = SimpleNamespace(id="so-1")
        svc.get_order_read_model.return_value = {
            "id": "so-1", "name": "Outside coating", "item_id": None, "routing_id": None,
            "source_operation_id": None, "state": "draft", "vendor_id": "vendor-9", "vendor_name": "New Vendor",
            "requested_qty": 5.0, "issued_qty": 0.0, "received_qty": 0.0, "open_qty": 5.0,
            "completion_pct": 0.0, "timeline_total": 0, "operation": {"operation_id": None, "routing_id": None, "operation_number": None, "name": None, "is_subcontracted": False, "subcontractor_id": None},
        }
        svc.record_material_issue.return_value = SimpleNamespace(
            id="evt-1", order_id="so-1", event_type="material_issue", quantity=5.0, reference="ISS-1", note=None, created_at=None,
        )
        svc.record_receipt.return_value = SimpleNamespace(
            id="evt-2", order_id="so-1", event_type="receipt", quantity=5.0, reference="RCV-1", note=None, created_at=None,
        )
        svc.get_order.return_value = SimpleNamespace(id="so-1")
        svc.get_timeline.return_value = [svc.record_material_issue.return_value, svc.record_receipt.return_value]

        assign_response = client.post("/api/v1/subcontracting/orders/so-1/assign-vendor", json={"vendor_id": "vendor-9", "vendor_name": "New Vendor"})
        issue_response = client.post("/api/v1/subcontracting/orders/so-1/issue-material", json={"quantity": 5, "reference": "ISS-1"})
        receipt_response = client.post("/api/v1/subcontracting/orders/so-1/record-receipt", json={"quantity": 5, "reference": "RCV-1"})
        timeline_response = client.get("/api/v1/subcontracting/orders/so-1/timeline")

    assert assign_response.status_code == 200
    assert assign_response.json()["vendor_id"] == "vendor-9"
    assert issue_response.status_code == 200
    assert issue_response.json()["event_type"] == "material_issue"
    assert receipt_response.status_code == 200
    assert receipt_response.json()["event_type"] == "receipt"
    assert timeline_response.status_code == 200
    assert timeline_response.json()["total"] == 2
    assert db.commit.call_count == 3


def test_subcontracting_routes_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/subcontracting/orders" in paths
    assert "/api/v1/subcontracting/orders/{order_id}/assign-vendor" in paths
    assert "/api/v1/subcontracting/orders/{order_id}/issue-material" in paths
    assert "/api/v1/subcontracting/orders/{order_id}/record-receipt" in paths
    assert "/api/v1/subcontracting/overview" in paths
    assert "/api/v1/subcontracting/vendors/analytics" in paths
    assert "/api/v1/subcontracting/receipts/analytics" in paths


def test_subcontracting_analytics_endpoints():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.subcontracting_router.SubcontractingService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_overview.return_value = {"orders_total": 2, "vendors_total": 1}
        svc.get_vendor_analytics.return_value = {"vendors": [{"vendor_id": "v-1"}]}
        svc.get_receipt_analytics.return_value = {"receipts": [{"order_id": "so-1"}]}

        overview_response = client.get("/api/v1/subcontracting/overview")
        vendors_response = client.get("/api/v1/subcontracting/vendors/analytics")
        receipts_response = client.get("/api/v1/subcontracting/receipts/analytics")

    assert overview_response.status_code == 200
    assert overview_response.json()["orders_total"] == 2
    assert vendors_response.status_code == 200
    assert vendors_response.json()["vendors"][0]["vendor_id"] == "v-1"
    assert receipts_response.status_code == 200
    assert receipts_response.json()["receipts"][0]["order_id"] == "so-1"


def test_subcontracting_export_endpoints():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.subcontracting_router.SubcontractingService") as svc_cls:
        svc = svc_cls.return_value
        svc.export_overview.return_value = {"orders_total": 2}
        svc.export_vendor_analytics.return_value = "vendor_id,orders_total\nv-1,1\n"
        svc.export_receipt_analytics.return_value = {"receipts": [{"order_id": "so-1"}]}

        overview_response = client.get("/api/v1/subcontracting/export/overview", params={"format": "json"})
        vendors_response = client.get("/api/v1/subcontracting/export/vendors", params={"format": "csv"})
        receipts_response = client.get("/api/v1/subcontracting/export/receipts", params={"format": "json"})

    assert overview_response.status_code == 200
    assert overview_response.headers["content-disposition"].endswith('subcontracting-overview.json"')
    assert overview_response.json()["orders_total"] == 2
    assert vendors_response.status_code == 200
    assert vendors_response.headers["content-type"].startswith("text/csv")
    assert "vendor_id,orders_total" in vendors_response.text
    assert receipts_response.status_code == 200
    assert receipts_response.json()["receipts"][0]["order_id"] == "so-1"
