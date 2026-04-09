"""Tests for box_router (C17 PLM Box Bootstrap)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.meta_engine.web.box_router import box_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app():
    """Standalone FastAPI app with box_router mounted."""
    app = FastAPI()
    app.include_router(box_router, prefix="/api/v1")
    return app


def _client_with_mocks():
    """Return TestClient with mocked DB and user dependencies."""
    from yuantus.api.dependencies.auth import get_current_user
    from yuantus.database import get_db

    mock_db = MagicMock()
    user = SimpleNamespace(id=100, roles=["engineer"], is_superuser=False)

    app = _make_app()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_item():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        fake_box = SimpleNamespace(
            id="box-1", name="Small Box", description=None, box_type="box",
            state="draft", width=100.0, height=80.0, depth=50.0,
            dimension_unit="mm", tare_weight=0.2, max_gross_weight=5.0,
            weight_unit="kg", material="cardboard", barcode="123",
            max_quantity=20, cost=1.0, product_id=None, is_active=True,
        )
        svc_cls.return_value.create_box.return_value = fake_box

        resp = client.post("/api/v1/box/items", json={"name": "Small Box"})

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["name"] == "Small Box"
    assert db.commit.called


def test_list_items():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        fake_box = SimpleNamespace(
            id="box-1", name="A", description=None, box_type="box",
            state="draft", width=None, height=None, depth=None,
            dimension_unit="mm", tare_weight=None, max_gross_weight=None,
            weight_unit="kg", material=None, barcode=None,
            max_quantity=None, cost=None, product_id=None, is_active=True,
        )
        svc_cls.return_value.list_boxes.return_value = [fake_box]

        resp = client.get("/api/v1/box/items")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_get_item():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        fake_box = SimpleNamespace(
            id="box-1", name="A", description=None, box_type="box",
            state="draft", width=None, height=None, depth=None,
            dimension_unit="mm", tare_weight=None, max_gross_weight=None,
            weight_unit="kg", material=None, barcode=None,
            max_quantity=None, cost=None, product_id=None, is_active=True,
        )
        svc_cls.return_value.get_box.return_value = fake_box

        resp = client.get("/api/v1/box/items/box-1")

    assert resp.status_code == 200
    assert resp.json()["id"] == "box-1"


def test_get_contents():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.get_box.return_value = SimpleNamespace(id="box-1")
        fake_content = SimpleNamespace(
            id="c-1", box_id="box-1", item_id="item-1",
            quantity=3.0, lot_serial=None, note=None,
        )
        svc_cls.return_value.list_contents.return_value = [fake_content]

        resp = client.get("/api/v1/box/items/box-1/contents")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["contents"][0]["item_id"] == "item-1"


def test_export_meta():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_meta.return_value = {
            "id": "box-1",
            "name": "Box",
            "box_type": "box",
            "state": "draft",
            "dimensions": {"width": 100, "height": 80, "depth": 50, "unit": "mm"},
            "weight": {"tare": 0.2, "max_gross": 5.0, "unit": "kg"},
            "material": "cardboard",
            "barcode": "123",
            "max_quantity": 20,
            "cost": 1.0,
            "product_id": None,
            "is_active": True,
            "contents": [],
        }

        resp = client.get("/api/v1/box/items/box-1/export-meta")

    assert resp.status_code == 200
    assert resp.json()["id"] == "box-1"
    assert "dimensions" in resp.json()
    assert "contents" in resp.json()


def test_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.get_box.return_value = None

        resp = client.get("/api/v1/box/items/nonexistent")

    assert resp.status_code == 404


def test_create_invalid_400():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.create_box.side_effect = ValueError("Invalid box_type")

        resp = client.post(
            "/api/v1/box/items",
            json={"name": "Bad", "box_type": "spaceship"},
        )

    assert resp.status_code == 400
    assert "Invalid box_type" in resp.json()["detail"]
    assert db.rollback.called


# ---------------------------------------------------------------------------
# Analytics / export endpoint tests (C20)
# ---------------------------------------------------------------------------


def test_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.overview.return_value = {
            "total": 5, "active": 3,
            "by_state": {"draft": 2, "active": 3},
            "by_type": {"box": 4, "pallet": 1},
            "total_cost": 25.0,
        }
        resp = client.get("/api/v1/box/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 5
    assert resp.json()["by_type"]["box"] == 4


def test_material_analytics():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.material_analytics.return_value = {
            "total": 3,
            "by_material": {"cardboard": 2, "wood": 1},
            "no_material": 0,
        }
        resp = client.get("/api/v1/box/materials/analytics")

    assert resp.status_code == 200
    assert resp.json()["by_material"]["cardboard"] == 2


def test_contents_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.contents_summary.return_value = {
            "box_id": "box-1", "box_name": "Test",
            "total_lines": 3, "distinct_items": 2,
            "total_quantity": 10.0, "has_lot_serial": 1,
        }
        resp = client.get("/api/v1/box/items/box-1/contents-summary")

    assert resp.status_code == 200
    assert resp.json()["total_lines"] == 3
    assert resp.json()["distinct_items"] == 2


def test_contents_summary_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.contents_summary.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/x/contents-summary")

    assert resp.status_code == 404


def test_export_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_overview.return_value = {
            "overview": {"total": 2, "active": 1, "by_state": {}, "by_type": {}, "total_cost": 0},
            "material_analytics": {"total": 2, "by_material": {}, "no_material": 2},
        }
        resp = client.get("/api/v1/box/export/overview")

    assert resp.status_code == 200
    assert "overview" in resp.json()
    assert "material_analytics" in resp.json()


def test_export_contents():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_contents.return_value = {
            "box_id": "box-1", "box_name": "Test",
            "total_lines": 1, "distinct_items": 1,
            "total_quantity": 5.0, "has_lot_serial": 0,
            "contents": [{"id": "c-1", "item_id": "i-1", "quantity": 5.0, "lot_serial": None, "note": None}],
        }
        resp = client.get("/api/v1/box/items/box-1/export-contents")

    assert resp.status_code == 200
    assert resp.json()["total_lines"] == 1
    assert len(resp.json()["contents"]) == 1


def test_export_contents_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_contents.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/x/export-contents")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Ops report / transitions endpoint tests (C23)
# ---------------------------------------------------------------------------


def test_transition_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.transition_summary.return_value = {
            "total": 4,
            "by_state": {"draft": 2, "active": 1, "archived": 1},
            "draft_to_active_eligible": 2,
            "active_to_archive_eligible": 1,
        }
        resp = client.get("/api/v1/box/transitions/summary")

    assert resp.status_code == 200
    assert resp.json()["total"] == 4
    assert resp.json()["draft_to_active_eligible"] == 2
    assert resp.json()["active_to_archive_eligible"] == 1


def test_active_archive_breakdown():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.active_archive_breakdown.return_value = {
            "active": {"count": 3, "total_cost": 15.0, "by_type": {"box": 2, "carton": 1}},
            "archived": {"count": 1, "total_cost": 5.0, "by_type": {"box": 1}},
        }
        resp = client.get("/api/v1/box/active-archive/breakdown")

    assert resp.status_code == 200
    assert resp.json()["active"]["count"] == 3
    assert resp.json()["active"]["total_cost"] == 15.0
    assert resp.json()["archived"]["count"] == 1


def test_ops_report():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.ops_report.return_value = {
            "box_id": "box-1",
            "name": "Test Box",
            "state": "draft",
            "box_type": "box",
            "can_activate": True,
            "can_archive": False,
            "is_terminal": False,
            "contents_count": 2,
            "total_quantity": 8.0,
            "material": "cardboard",
            "cost": 2.5,
        }
        resp = client.get("/api/v1/box/items/box-1/ops-report")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["can_activate"] is True
    assert resp.json()["can_archive"] is False
    assert resp.json()["contents_count"] == 2


def test_ops_report_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.ops_report.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/ops-report")

    assert resp.status_code == 404


def test_export_ops_report():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_ops_report.return_value = {
            "transition_summary": {
                "total": 3,
                "by_state": {"draft": 1, "active": 1, "archived": 1},
                "draft_to_active_eligible": 1,
                "active_to_archive_eligible": 1,
            },
            "active_archive_breakdown": {
                "active": {"count": 1, "total_cost": 5.0, "by_type": {"box": 1}},
                "archived": {"count": 1, "total_cost": 3.0, "by_type": {"carton": 1}},
            },
        }
        resp = client.get("/api/v1/box/export/ops-report")

    assert resp.status_code == 200
    assert "transition_summary" in resp.json()
    assert "active_archive_breakdown" in resp.json()
    assert resp.json()["transition_summary"]["total"] == 3
    assert resp.json()["active_archive_breakdown"]["active"]["count"] == 1


# ---------------------------------------------------------------------------
# Reconciliation / audit endpoint tests (C26)
# ---------------------------------------------------------------------------


def test_reconciliation_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.reconciliation_overview.return_value = {
            "total": 5,
            "with_contents": 3,
            "without_contents": 2,
            "with_barcode": 4,
            "without_barcode": 1,
            "with_dimensions": 3,
            "with_weight": 4,
            "completeness_pct": 73.3,
        }
        resp = client.get("/api/v1/box/reconciliation/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 5
    assert resp.json()["with_barcode"] == 4
    assert resp.json()["completeness_pct"] == 73.3


def test_audit_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.audit_summary.return_value = {
            "total": 3,
            "no_material": 1,
            "no_material_ids": ["b2"],
            "no_dimensions": 1,
            "no_dimensions_ids": ["b2"],
            "no_cost": 1,
            "no_cost_ids": ["b2"],
            "archived_with_contents": 0,
            "archived_with_contents_ids": [],
        }
        resp = client.get("/api/v1/box/audit/summary")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["no_material"] == 1
    assert "b2" in resp.json()["no_material_ids"]


def test_box_item_reconciliation():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_reconciliation.return_value = {
            "box_id": "box-1",
            "name": "Test Box",
            "state": "active",
            "has_material": True,
            "has_dimensions": True,
            "has_weight": True,
            "has_barcode": True,
            "has_cost": True,
            "checks_passed": 5,
            "checks_total": 5,
            "contents_count": 2,
            "total_quantity": 8.0,
        }
        resp = client.get("/api/v1/box/items/box-1/reconciliation")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["checks_passed"] == 5
    assert resp.json()["contents_count"] == 2


def test_box_item_reconciliation_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_reconciliation.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/reconciliation")

    assert resp.status_code == 404


def test_export_reconciliation():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_box_reconciliation.return_value = {
            "reconciliation_overview": {
                "total": 2, "with_contents": 1, "without_contents": 1,
                "with_barcode": 2, "without_barcode": 0,
                "with_dimensions": 1, "with_weight": 2, "completeness_pct": 83.3,
            },
            "audit_summary": {
                "total": 2, "no_material": 0, "no_material_ids": [],
                "no_dimensions": 1, "no_dimensions_ids": ["b2"],
                "no_cost": 0, "no_cost_ids": [],
                "archived_with_contents": 0, "archived_with_contents_ids": [],
            },
        }
        resp = client.get("/api/v1/box/export/reconciliation")

    assert resp.status_code == 200
    assert "reconciliation_overview" in resp.json()
    assert "audit_summary" in resp.json()
    assert resp.json()["reconciliation_overview"]["total"] == 2


# ---------------------------------------------------------------------------
# Capacity / Compliance endpoint tests (C29)
# ---------------------------------------------------------------------------


def test_capacity_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.capacity_overview.return_value = {
            "total": 3,
            "with_max_quantity": 2,
            "with_weight_limit": 2,
            "average_fill_rate": 45.0,
            "bands": {"high": 0, "medium": 1, "low": 1},
        }
        resp = client.get("/api/v1/box/capacity/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["with_max_quantity"] == 2
    assert resp.json()["average_fill_rate"] == 45.0
    assert resp.json()["bands"]["medium"] == 1


def test_compliance_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.compliance_summary.return_value = {
            "total": 4,
            "missing_dimensions": 1,
            "missing_weight": 2,
            "exceeding_weight_limit": 0,
            "over_capacity": 1,
            "compliant": 2,
            "non_compliant": 2,
        }
        resp = client.get("/api/v1/box/compliance/summary")

    assert resp.status_code == 200
    assert resp.json()["total"] == 4
    assert resp.json()["missing_dimensions"] == 1
    assert resp.json()["compliant"] == 2
    assert resp.json()["non_compliant"] == 2


def test_box_capacity():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_capacity.return_value = {
            "box_id": "box-1",
            "max_quantity": 10,
            "contents_count": 2,
            "fill_pct": 20.0,
            "has_weight_limit": True,
            "tare_weight": 1.0,
            "max_gross_weight": 50.0,
            "dimension_complete": True,
            "compliance_checks": {
                "missing_dimensions": False,
                "missing_weight": False,
                "over_capacity": False,
            },
        }
        resp = client.get("/api/v1/box/items/box-1/capacity")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["fill_pct"] == 20.0
    assert resp.json()["dimension_complete"] is True
    assert resp.json()["compliance_checks"]["over_capacity"] is False


def test_box_capacity_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_capacity.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/capacity")

    assert resp.status_code == 404


def test_export_capacity():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_capacity.return_value = {
            "capacity_overview": {
                "total": 2, "with_max_quantity": 1, "with_weight_limit": 1,
                "average_fill_rate": 30.0, "bands": {"high": 0, "medium": 0, "low": 1},
            },
            "compliance_summary": {
                "total": 2, "missing_dimensions": 1, "missing_weight": 0,
                "exceeding_weight_limit": 0, "over_capacity": 0,
                "compliant": 1, "non_compliant": 1,
            },
        }
        resp = client.get("/api/v1/box/export/capacity")

    assert resp.status_code == 200
    assert "capacity_overview" in resp.json()
    assert "compliance_summary" in resp.json()
    assert resp.json()["capacity_overview"]["total"] == 2
    assert resp.json()["compliance_summary"]["compliant"] == 1


# ---------------------------------------------------------------------------
# Policy / Exceptions endpoint tests (C32)
# ---------------------------------------------------------------------------


def test_policy_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.policy_overview.return_value = {
            "total": 3,
            "with_barcode": 2,
            "with_material": 2,
            "with_dimensions": 2,
            "with_cost": 2,
            "fully_compliant": 2,
            "policy_compliance_pct": 66.7,
        }
        resp = client.get("/api/v1/box/policy/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["with_barcode"] == 2
    assert resp.json()["fully_compliant"] == 2
    assert resp.json()["policy_compliance_pct"] == 66.7


def test_exceptions_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.exceptions_summary.return_value = {
            "missing_barcode": ["b2"],
            "missing_material": ["b2"],
            "missing_cost": ["b2"],
            "archived_active_contents": [],
            "over_max_quantity": [],
            "total_exceptions": 3,
        }
        resp = client.get("/api/v1/box/exceptions/summary")

    assert resp.status_code == 200
    assert resp.json()["total_exceptions"] == 3
    assert "b2" in resp.json()["missing_barcode"]
    assert resp.json()["archived_active_contents"] == []


def test_box_policy_check():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_policy_check.return_value = {
            "box_id": "box-1",
            "has_barcode": True,
            "has_material": True,
            "has_dimensions": True,
            "has_cost": True,
            "has_weight": True,
            "is_compliant": True,
            "exceptions": [],
        }
        resp = client.get("/api/v1/box/items/box-1/policy-check")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["is_compliant"] is True
    assert resp.json()["exceptions"] == []


def test_box_policy_check_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_policy_check.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/policy-check")

    assert resp.status_code == 404


def test_export_exceptions():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_exceptions.return_value = {
            "policy_overview": {
                "total": 2, "with_barcode": 1, "with_material": 2,
                "with_dimensions": 1, "with_cost": 2,
                "fully_compliant": 1, "policy_compliance_pct": 50.0,
            },
            "exceptions_summary": {
                "missing_barcode": ["b2"],
                "missing_material": [],
                "missing_cost": [],
                "archived_active_contents": [],
                "over_max_quantity": [],
                "total_exceptions": 1,
            },
        }
        resp = client.get("/api/v1/box/export/exceptions")

    assert resp.status_code == 200
    assert "policy_overview" in resp.json()
    assert "exceptions_summary" in resp.json()
    assert resp.json()["policy_overview"]["total"] == 2
    assert resp.json()["exceptions_summary"]["total_exceptions"] == 1


# ---------------------------------------------------------------------------
# Reservations / Traceability endpoint tests (C35)
# ---------------------------------------------------------------------------


def test_reservations_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.reservations_overview.return_value = {
            "total": 3,
            "by_state": {"active": 2, "draft": 1},
            "reserved": 2,
            "unreserved": 1,
            "average_fill_rate": 35.0,
        }
        resp = client.get("/api/v1/box/reservations/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["reserved"] == 2
    assert resp.json()["unreserved"] == 1
    assert resp.json()["average_fill_rate"] == 35.0
    assert resp.json()["by_state"]["active"] == 2


def test_traceability_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.traceability_summary.return_value = {
            "total_contents": 10,
            "with_lot_serial": 6,
            "without_lot_serial": 4,
            "boxes_with_traceability": 3,
            "boxes_without_traceability": 1,
            "traceability_pct": 60.0,
        }
        resp = client.get("/api/v1/box/traceability/summary")

    assert resp.status_code == 200
    assert resp.json()["total_contents"] == 10
    assert resp.json()["with_lot_serial"] == 6
    assert resp.json()["without_lot_serial"] == 4
    assert resp.json()["traceability_pct"] == 60.0


def test_box_reservations():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_reservations.return_value = {
            "box_id": "box-1",
            "box_name": "Test Box",
            "state": "active",
            "contents_count": 2,
            "max_quantity": 10,
            "fill_pct": 20.0,
            "lot_serial_count": 1,
            "lot_serial_pct": 50.0,
            "contents": [
                {"id": "c-1", "item_id": "i-1", "quantity": 5.0, "lot_serial": "LOT-001", "note": None},
                {"id": "c-2", "item_id": "i-2", "quantity": 3.0, "lot_serial": None, "note": "test"},
            ],
        }
        resp = client.get("/api/v1/box/items/box-1/reservations")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["contents_count"] == 2
    assert resp.json()["fill_pct"] == 20.0
    assert resp.json()["lot_serial_count"] == 1
    assert resp.json()["lot_serial_pct"] == 50.0
    assert len(resp.json()["contents"]) == 2


def test_box_reservations_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_reservations.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/reservations")

    assert resp.status_code == 404


def test_export_traceability():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_traceability.return_value = {
            "reservations_overview": {
                "total": 2, "by_state": {"active": 1, "draft": 1},
                "reserved": 1, "unreserved": 1, "average_fill_rate": 20.0,
            },
            "traceability_summary": {
                "total_contents": 3, "with_lot_serial": 2,
                "without_lot_serial": 1,
                "boxes_with_traceability": 1,
                "boxes_without_traceability": 0,
                "traceability_pct": 66.7,
            },
            "per_box_details": [
                {"box_id": "b1", "box_name": "Box 1",
                 "contents_count": 3, "lot_serial_count": 2, "fill_pct": 30.0},
            ],
        }
        resp = client.get("/api/v1/box/export/traceability")

    assert resp.status_code == 200
    assert "reservations_overview" in resp.json()
    assert "traceability_summary" in resp.json()
    assert "per_box_details" in resp.json()
    assert resp.json()["reservations_overview"]["total"] == 2
    assert resp.json()["traceability_summary"]["traceability_pct"] == 66.7
    assert len(resp.json()["per_box_details"]) == 1


# ---------------------------------------------------------------------------
# Allocation / Custody endpoint tests (C38)
# ---------------------------------------------------------------------------


def test_allocations_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.allocations_overview.return_value = {
            "total": 3,
            "allocated": 1,
            "unallocated": 2,
            "allocation_rate": 33.3,
            "by_state": {"active": 2, "draft": 1},
        }
        resp = client.get("/api/v1/box/allocations/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["allocated"] == 1
    assert resp.json()["unallocated"] == 2
    assert resp.json()["allocation_rate"] == 33.3
    assert resp.json()["by_state"]["active"] == 2


def test_custody_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.custody_summary.return_value = {
            "total": 3,
            "boxes_with_contents": 2,
            "max_custody_depth": 5,
            "avg_contents_per_box": 2.33,
        }
        resp = client.get("/api/v1/box/custody/summary")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["boxes_with_contents"] == 2
    assert resp.json()["max_custody_depth"] == 5
    assert resp.json()["avg_contents_per_box"] == 2.33


def test_box_custody():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_custody.return_value = {
            "box_id": "box-1",
            "box_name": "Test Box",
            "state": "active",
            "custody_depth": 2,
            "total_quantity": 8.0,
            "contents": [
                {"id": "c-1", "item_id": "i-1", "quantity": 5.0, "lot_serial": "LOT-001", "note": None},
                {"id": "c-2", "item_id": "i-2", "quantity": 3.0, "lot_serial": None, "note": "test"},
            ],
        }
        resp = client.get("/api/v1/box/items/box-1/custody")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["custody_depth"] == 2
    assert resp.json()["total_quantity"] == 8.0
    assert len(resp.json()["contents"]) == 2


def test_box_custody_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_custody.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/custody")

    assert resp.status_code == 404


def test_export_custody():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_custody.return_value = {
            "allocations_overview": {
                "total": 2, "allocated": 1, "unallocated": 1,
                "allocation_rate": 50.0, "by_state": {"active": 1, "draft": 1},
            },
            "custody_summary": {
                "total": 2, "boxes_with_contents": 1,
                "max_custody_depth": 3, "avg_contents_per_box": 1.5,
            },
            "per_box_custody": [
                {"box_id": "b1", "box_name": "Box 1", "state": "active",
                 "custody_depth": 3, "total_quantity": 10.0},
                {"box_id": "b2", "box_name": "Box 2", "state": "draft",
                 "custody_depth": 0, "total_quantity": 0.0},
            ],
        }
        resp = client.get("/api/v1/box/export/custody")

    assert resp.status_code == 200
    assert "allocations_overview" in resp.json()
    assert "custody_summary" in resp.json()
    assert "per_box_custody" in resp.json()
    assert resp.json()["allocations_overview"]["total"] == 2
    assert resp.json()["custody_summary"]["boxes_with_contents"] == 1
    assert len(resp.json()["per_box_custody"]) == 2


# ---------------------------------------------------------------------------
# Occupancy / Turnover endpoint tests (C41)
# ---------------------------------------------------------------------------


def test_occupancy_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.occupancy_overview.return_value = {
            "total": 3,
            "occupied": 2,
            "empty": 1,
            "occupancy_rate": 66.7,
            "avg_fill_level": 45.0,
        }
        resp = client.get("/api/v1/box/occupancy/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert resp.json()["occupied"] == 2
    assert resp.json()["empty"] == 1
    assert resp.json()["occupancy_rate"] == 66.7
    assert resp.json()["avg_fill_level"] == 45.0


def test_turnover_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.turnover_summary.return_value = {
            "total": 4,
            "active_boxes": 3,
            "avg_contents_per_active": 2.67,
            "high_turnover": 1,
            "low_turnover": 1,
        }
        resp = client.get("/api/v1/box/turnover/summary")

    assert resp.status_code == 200
    assert resp.json()["total"] == 4
    assert resp.json()["active_boxes"] == 3
    assert resp.json()["avg_contents_per_active"] == 2.67
    assert resp.json()["high_turnover"] == 1
    assert resp.json()["low_turnover"] == 1


def test_box_turnover():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_turnover.return_value = {
            "box_id": "box-1",
            "box_name": "Test Box",
            "state": "active",
            "contents_count": 3,
            "max_quantity": 10,
            "fill_ratio": 30.0,
            "classification": "normal",
        }
        resp = client.get("/api/v1/box/items/box-1/turnover")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["contents_count"] == 3
    assert resp.json()["fill_ratio"] == 30.0
    assert resp.json()["classification"] == "normal"


def test_box_turnover_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_turnover.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/turnover")

    assert resp.status_code == 404


def test_export_turnover():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_turnover.return_value = {
            "occupancy_overview": {
                "total": 2, "occupied": 1, "empty": 1,
                "occupancy_rate": 50.0, "avg_fill_level": 30.0,
            },
            "turnover_summary": {
                "total": 2, "active_boxes": 1,
                "avg_contents_per_active": 3.0,
                "high_turnover": 0, "low_turnover": 0,
            },
            "per_box_turnover": [
                {"box_id": "b1", "box_name": "Box 1", "state": "active",
                 "contents_count": 3, "fill_ratio": 30.0, "classification": "normal"},
                {"box_id": "b2", "box_name": "Box 2", "state": "draft",
                 "contents_count": 0, "fill_ratio": 0.0, "classification": "low"},
            ],
        }
        resp = client.get("/api/v1/box/export/turnover")

    assert resp.status_code == 200
    assert "occupancy_overview" in resp.json()
    assert "turnover_summary" in resp.json()
    assert "per_box_turnover" in resp.json()
    assert resp.json()["occupancy_overview"]["total"] == 2
    assert resp.json()["turnover_summary"]["active_boxes"] == 1
    assert len(resp.json()["per_box_turnover"]) == 2


# ---------------------------------------------------------------------------
# Dwell / Aging endpoints (C44)
# ---------------------------------------------------------------------------


def test_dwell_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.dwell_overview.return_value = {
            "total": 5,
            "avg_items_per_box": 3.4,
            "high_dwell": 1,
            "high_dwell_ids": ["b1"],
            "low_dwell": 2,
            "low_dwell_ids": ["b3", "b4"],
        }
        resp = client.get("/api/v1/box/dwell/overview")

    assert resp.status_code == 200
    assert resp.json()["total"] == 5
    assert resp.json()["avg_items_per_box"] == 3.4
    assert resp.json()["high_dwell"] == 1
    assert resp.json()["low_dwell"] == 2


def test_aging_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.aging_summary.return_value = {
            "total": 6,
            "mature": 1,
            "mature_ids": ["b1"],
            "active": 2,
            "active_ids": ["b2", "b3"],
            "fresh": 3,
            "fresh_ids": ["b4", "b5", "b6"],
        }
        resp = client.get("/api/v1/box/aging/summary")

    assert resp.status_code == 200
    assert resp.json()["total"] == 6
    assert resp.json()["mature"] == 1
    assert resp.json()["active"] == 2
    assert resp.json()["fresh"] == 3


def test_box_aging():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_aging.return_value = {
            "box_id": "box-1",
            "box_name": "Test Box",
            "state": "active",
            "item_count": 5,
            "age_tier": "active",
            "total_quantity": 15.0,
            "contents": [],
        }
        resp = client.get("/api/v1/box/items/box-1/aging")

    assert resp.status_code == 200
    assert resp.json()["box_id"] == "box-1"
    assert resp.json()["item_count"] == 5
    assert resp.json()["age_tier"] == "active"
    assert resp.json()["total_quantity"] == 15.0


def test_box_aging_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.box_aging.side_effect = ValueError("not found")
        resp = client.get("/api/v1/box/items/nonexistent/aging")

    assert resp.status_code == 404


def test_export_aging():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_aging.return_value = {
            "dwell_overview": {
                "total": 2, "avg_items_per_box": 4.0,
                "high_dwell": 0, "high_dwell_ids": [],
                "low_dwell": 1, "low_dwell_ids": ["b2"],
            },
            "aging_summary": {
                "total": 2, "mature": 0, "mature_ids": [],
                "active": 1, "active_ids": ["b1"],
                "fresh": 1, "fresh_ids": ["b2"],
            },
            "per_box_aging": [
                {"box_id": "b1", "box_name": "Box 1", "state": "active",
                 "item_count": 5, "age_tier": "active", "total_quantity": 10.0},
                {"box_id": "b2", "box_name": "Box 2", "state": "draft",
                 "item_count": 1, "age_tier": "fresh", "total_quantity": 2.0},
            ],
        }
        resp = client.get("/api/v1/box/export/aging")

    assert resp.status_code == 200
    assert "dwell_overview" in resp.json()
    assert "aging_summary" in resp.json()
    assert "per_box_aging" in resp.json()
    assert resp.json()["dwell_overview"]["total"] == 2
    assert resp.json()["aging_summary"]["active"] == 1
    assert len(resp.json()["per_box_aging"]) == 2
