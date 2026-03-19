"""Tests for C19 – Cutted-parts router."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user
from yuantus.meta_engine.web.cutted_parts_router import cutted_parts_router


def _client_with_user():
    mock_db = MagicMock()
    mock_user = SimpleNamespace(id=1, username="tester")

    def override_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(cutted_parts_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app), mock_db


def _fake_plan(**overrides):
    defaults = dict(
        id="plan-1", name="Test Plan", description=None,
        state="draft", material_id=None, material_quantity=1.0,
        total_parts=0, ok_count=0, scrap_count=0, rework_count=0,
        waste_pct=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_cut(**overrides):
    defaults = dict(
        id="cut-1", plan_id="plan-1", part_id=None,
        length=100.0, width=50.0, quantity=1.0,
        status="ok", scrap_weight=None, note=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_material(**overrides):
    defaults = dict(
        id="mat-1", name="Steel Sheet", material_type="sheet",
        grade="304", length=2000.0, width=1000.0, thickness=1.5,
        dimension_unit="mm", weight_per_unit=23.6, weight_unit="kg",
        stock_quantity=100.0, cost_per_unit=45.0, is_active=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Plan endpoints
# ---------------------------------------------------------------------------


def test_create_plan():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.create_plan.return_value = _fake_plan()
        resp = client.post(
            "/api/v1/cutted-parts/plans",
            json={"name": "Test Plan"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["id"] == "plan-1"


def test_create_plan_invalid_400():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.create_plan.side_effect = ValueError("material not found")
        resp = client.post(
            "/api/v1/cutted-parts/plans",
            json={"name": "Bad Plan"},
        )
    assert resp.status_code == 400
    assert "material not found" in resp.json()["detail"]


def test_list_plans():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.list_plans.return_value = [_fake_plan(), _fake_plan(id="plan-2", name="Plan 2")]
        resp = client.get("/api/v1/cutted-parts/plans")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_get_plan():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.get_plan.return_value = _fake_plan()
        resp = client.get("/api/v1/cutted-parts/plans/plan-1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Plan"


def test_get_plan_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.get_plan.return_value = None
        resp = client.get("/api/v1/cutted-parts/plans/nonexistent")
    assert resp.status_code == 404


def test_get_plan_summary():
    client, db = _client_with_user()
    summary = {
        "plan_id": "plan-1", "name": "Test Plan", "state": "draft",
        "material_id": None, "material_quantity": 1.0,
        "total_cuts": 3, "total_quantity": 6.0,
        "by_status": {"ok": 2, "scrap": 1},
        "total_scrap_weight": 0.5, "waste_pct": 3.2,
    }
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_summary.return_value = summary
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/summary")
    assert resp.status_code == 200
    assert resp.json()["total_cuts"] == 3


def test_get_plan_summary_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_summary.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/summary")
    assert resp.status_code == 404


def test_list_cuts():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.get_plan.return_value = _fake_plan()
        service.list_cuts.return_value = [_fake_cut(), _fake_cut(id="cut-2")]
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/cuts")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_list_cuts_plan_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.get_plan.return_value = None
        resp = client.get("/api/v1/cutted-parts/plans/nonexistent/cuts")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Material endpoints
# ---------------------------------------------------------------------------


def test_list_materials():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.list_materials.return_value = [_fake_material()]
        resp = client.get("/api/v1/cutted-parts/materials")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["materials"][0]["name"] == "Steel Sheet"


# ---------------------------------------------------------------------------
# Analytics / export endpoints (C22)
# ---------------------------------------------------------------------------


def test_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.overview.return_value = {
            "total_plans": 3, "plans_by_state": {"draft": 2, "completed": 1},
            "total_materials": 5, "total_parts": 20,
            "total_ok": 15, "total_scrap": 3, "total_rework": 2,
        }
        resp = client.get("/api/v1/cutted-parts/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3


def test_material_analytics():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.material_analytics.return_value = {
            "total_materials": 2, "active_count": 2,
            "by_type": {"sheet": 1, "bar": 1},
            "total_stock_quantity": 150.0, "total_cost_value": 2000.0,
        }
        resp = client.get("/api/v1/cutted-parts/materials/analytics")
    assert resp.status_code == 200
    assert resp.json()["total_materials"] == 2


def test_waste_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.waste_summary.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "total_cuts": 3, "ok_count": 1, "scrap_count": 1, "rework_count": 1,
            "total_quantity": 5.0, "total_scrap_weight": 0.5,
            "waste_pct": 8.5, "utilization_pct": 33.33,
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/waste-summary")
    assert resp.status_code == 200
    assert resp.json()["total_cuts"] == 3
    assert resp.json()["utilization_pct"] == 33.33


def test_waste_summary_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.waste_summary.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/waste-summary")
    assert resp.status_code == 404


def test_export_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_overview.return_value = {
            "overview": {"total_plans": 1},
            "material_analytics": {"total_materials": 1},
        }
        resp = client.get("/api/v1/cutted-parts/export/overview")
    assert resp.status_code == 200
    assert "overview" in resp.json()
    assert "material_analytics" in resp.json()


def test_export_waste():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_waste.return_value = {
            "total_plans": 1,
            "plans": [{"plan_id": "p1", "plan_name": "P1", "state": "draft",
                        "total_cuts": 2, "scrap_count": 1,
                        "total_scrap_weight": 0.3, "waste_pct": 5.0}],
        }
        resp = client.get("/api/v1/cutted-parts/export/waste")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 1
    assert len(resp.json()["plans"]) == 1
