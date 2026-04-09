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


# ---------------------------------------------------------------------------
# Cost / Utilization endpoints (C25)
# ---------------------------------------------------------------------------


def test_utilization_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.utilization_overview.return_value = {
            "total_plans": 3, "plans_with_data": 2,
            "avg_utilization_pct": 75.0,
            "high_utilization": 1, "medium_utilization": 1, "low_utilization": 0,
        }
        resp = client.get("/api/v1/cutted-parts/utilization/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["avg_utilization_pct"] == 75.0


def test_material_utilization():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.material_utilization.return_value = {
            "total_materials": 2, "total_stock": 200.0, "total_consumed": 80.0,
            "materials": [
                {"material_id": "m1", "material_name": "Steel",
                 "material_type": "sheet", "stock_quantity": 100.0,
                 "consumed_quantity": 50.0, "remaining_quantity": 50.0,
                 "plan_count": 2, "consumption_pct": 50.0},
            ],
        }
        resp = client.get("/api/v1/cutted-parts/materials/utilization")
    assert resp.status_code == 200
    assert resp.json()["total_materials"] == 2
    assert len(resp.json()["materials"]) == 1


def test_plan_cost_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_cost_summary.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "material_id": "mat-1", "material_name": "Steel",
            "material_quantity": 5.0, "cost_per_unit": 10.0,
            "material_cost": 50.0, "total_cuts": 3, "ok_count": 2,
            "total_scrap_weight": 0.3, "cost_per_good_part": 25.0,
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/cost-summary")
    assert resp.status_code == 200
    assert resp.json()["material_cost"] == 50.0
    assert resp.json()["cost_per_good_part"] == 25.0


def test_plan_cost_summary_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_cost_summary.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/cost-summary")
    assert resp.status_code == 404


def test_export_utilization():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_utilization.return_value = {
            "utilization_overview": {"total_plans": 1},
            "material_utilization": {"total_materials": 1},
        }
        resp = client.get("/api/v1/cutted-parts/export/utilization")
    assert resp.status_code == 200
    assert "utilization_overview" in resp.json()
    assert "material_utilization" in resp.json()


def test_export_costs():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_costs.return_value = {
            "total_plans": 1, "total_material_cost": 30.0,
            "plans": [{"plan_id": "p1", "material_cost": 30.0}],
        }
        resp = client.get("/api/v1/cutted-parts/export/costs")
    assert resp.status_code == 200
    assert resp.json()["total_material_cost"] == 30.0
    assert len(resp.json()["plans"]) == 1


# ---------------------------------------------------------------------------
# Templates / Scenarios endpoints (C28)
# ---------------------------------------------------------------------------


def test_template_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.template_overview.return_value = {
            "template_count": 3, "active_scenarios": 2,
            "completed_scenarios": 1,
            "material_breakdown": [
                {"material_id": "m1", "material_name": "Steel", "plan_count": 2},
            ],
        }
        resp = client.get("/api/v1/cutted-parts/templates/overview")
    assert resp.status_code == 200
    assert resp.json()["template_count"] == 3
    assert resp.json()["active_scenarios"] == 2


def test_scenario_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.scenario_summary.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "total_cuts": 3, "ok_count": 1, "scrap_count": 1, "rework_count": 1,
            "total_scrap_weight": 0.5, "waste_pct": 8.0,
            "fleet_avg_waste_pct": 8.0, "waste_delta": 0.0,
            "material_cost": 50.0,
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/scenarios")
    assert resp.status_code == 200
    assert resp.json()["total_cuts"] == 3
    assert resp.json()["waste_delta"] == 0.0


def test_scenario_summary_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.scenario_summary.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/scenarios")
    assert resp.status_code == 404


def test_material_templates():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.material_templates.return_value = {
            "total_materials": 2,
            "by_type": {
                "sheet": [{"material_id": "m1", "material_name": "Steel",
                           "grade": "304", "stock_quantity": 100.0,
                           "cost_per_unit": 10.0, "is_active": True,
                           "plan_count": 2}],
            },
        }
        resp = client.get("/api/v1/cutted-parts/materials/templates")
    assert resp.status_code == 200
    assert resp.json()["total_materials"] == 2
    assert "sheet" in resp.json()["by_type"]


def test_export_scenarios():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_scenarios.return_value = {
            "template_overview": {"template_count": 1},
            "material_templates": {"total_materials": 1},
            "scenarios": [{"plan_id": "p1", "plan_name": "Plan 1"}],
        }
        resp = client.get("/api/v1/cutted-parts/export/scenarios")
    assert resp.status_code == 200
    assert "template_overview" in resp.json()
    assert "material_templates" in resp.json()
    assert len(resp.json()["scenarios"]) == 1


# ---------------------------------------------------------------------------
# Benchmark / Quote endpoints (C31)
# ---------------------------------------------------------------------------


def test_benchmark_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.benchmark_overview.return_value = {
            "total_plans": 3, "completed_plans": 1,
            "plans_with_waste_data": 2,
            "min_waste_pct": 3.0, "max_waste_pct": 7.0, "avg_waste_pct": 5.0,
            "best_plan_id": "p1", "best_plan_name": "Plan A",
            "min_material_cost": 50.0, "max_material_cost": 80.0,
        }
        resp = client.get("/api/v1/cutted-parts/benchmark/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["avg_waste_pct"] == 5.0
    assert resp.json()["best_plan_id"] == "p1"


def test_quote_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.quote_summary.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "material_name": "Steel", "material_quantity": 5.0,
            "cost_per_unit": 10.0, "material_cost": 50.0,
            "total_cuts": 3, "ok_count": 2, "scrap_count": 1,
            "total_scrap_weight": 0.5, "waste_pct": 6.0,
            "yield_pct": 66.67, "cost_per_good_part": 25.0,
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/quote-summary")
    assert resp.status_code == 200
    assert resp.json()["yield_pct"] == 66.67
    assert resp.json()["cost_per_good_part"] == 25.0


def test_quote_summary_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.quote_summary.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/quote-summary")
    assert resp.status_code == 404


def test_material_benchmarks():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.material_benchmarks.return_value = {
            "total_materials": 2,
            "benchmarks": [
                {"material_id": "m1", "material_name": "Steel",
                 "material_type": "sheet", "plan_count": 2,
                 "avg_waste_pct": 7.0, "total_material_cost": 100.0,
                 "stock_quantity": 100.0, "cost_per_unit": 10.0},
            ],
        }
        resp = client.get("/api/v1/cutted-parts/materials/benchmarks")
    assert resp.status_code == 200
    assert resp.json()["total_materials"] == 2
    assert len(resp.json()["benchmarks"]) == 1


def test_export_quotes():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_quotes.return_value = {
            "benchmark_overview": {"total_plans": 1},
            "material_benchmarks": {"total_materials": 1},
            "quotes": [{"plan_id": "p1", "plan_name": "Plan 1"}],
        }
        resp = client.get("/api/v1/cutted-parts/export/quotes")
    assert resp.status_code == 200
    assert "benchmark_overview" in resp.json()
    assert "material_benchmarks" in resp.json()
    assert len(resp.json()["quotes"]) == 1


# ---------------------------------------------------------------------------
# Variance / Recommendations endpoints (C34)
# ---------------------------------------------------------------------------


def test_variance_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.variance_overview.return_value = {
            "total_plans": 3, "plans_with_waste_data": 2,
            "waste_mean": 7.0, "waste_std": 3.0, "waste_range": 6.0,
            "cost_mean": 65.0, "cost_std": 15.0,
            "outlier_plan_ids": ["p3"], "outlier_count": 1,
        }
        resp = client.get("/api/v1/cutted-parts/variance/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["waste_mean"] == 7.0
    assert resp.json()["outlier_count"] == 1


def test_plan_recommendations():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_recommendations.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "total_cuts": 3, "ok_count": 2, "scrap_count": 1,
            "total_scrap_weight": 0.5, "waste_pct": 6.0,
            "fleet_avg_waste_pct": 5.0, "waste_delta": 1.0,
            "yield_pct": 66.67, "severity": "medium",
            "recommendations": ["Waste above fleet average — consider material optimization"],
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/recommendations")
    assert resp.status_code == 200
    assert resp.json()["severity"] == "medium"
    assert len(resp.json()["recommendations"]) == 1


def test_plan_recommendations_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_recommendations.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/recommendations")
    assert resp.status_code == 404


def test_material_variance():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.material_variance.return_value = {
            "total_materials": 2,
            "materials": [
                {"material_id": "m1", "material_name": "Steel",
                 "material_type": "sheet", "plan_count": 2,
                 "waste_mean": 7.0, "waste_std": 3.0,
                 "total_material_cost": 100.0, "stock_quantity": 100.0},
            ],
        }
        resp = client.get("/api/v1/cutted-parts/materials/variance")
    assert resp.status_code == 200
    assert resp.json()["total_materials"] == 2
    assert len(resp.json()["materials"]) == 1


def test_export_recommendations():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_recommendations.return_value = {
            "variance_overview": {"total_plans": 1},
            "material_variance": {"total_materials": 1},
            "recommendations": [{"plan_id": "p1", "plan_name": "Plan 1", "severity": "ok"}],
        }
        resp = client.get("/api/v1/cutted-parts/export/recommendations")
    assert resp.status_code == 200
    assert "variance_overview" in resp.json()
    assert "material_variance" in resp.json()
    assert len(resp.json()["recommendations"]) == 1


# ---------------------------------------------------------------------------
# Thresholds / Envelopes endpoints (C37)
# ---------------------------------------------------------------------------


def test_thresholds_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.thresholds_overview.return_value = {
            "total_plans": 3,
            "waste_threshold": 10.0, "scrap_threshold": 0.30, "yield_threshold": 50.0,
            "waste_breach_count": 1, "waste_breach_plan_ids": ["p2"],
            "scrap_breach_count": 0, "scrap_breach_plan_ids": [],
            "yield_breach_count": 1, "yield_breach_plan_ids": ["p3"],
        }
        resp = client.get("/api/v1/cutted-parts/thresholds/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["waste_breach_count"] == 1
    assert resp.json()["yield_breach_count"] == 1


def test_envelopes_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.envelopes_summary.return_value = {
            "total_materials": 2, "envelope_limit": 15.0,
            "within_count": 1, "exceeded_count": 1,
            "materials": [
                {"material_id": "m1", "material_name": "Steel",
                 "plan_count": 2, "envelope_min": 4.0, "envelope_max": 12.0,
                 "envelope_limit": 15.0, "within_envelope": True},
            ],
        }
        resp = client.get("/api/v1/cutted-parts/envelopes/summary")
    assert resp.status_code == 200
    assert resp.json()["total_materials"] == 2
    assert resp.json()["within_count"] == 1
    assert len(resp.json()["materials"]) == 1


def test_plan_threshold_check():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_threshold_check.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "total_cuts": 3, "ok_count": 2, "scrap_count": 1,
            "waste_pct": 8.0, "waste_threshold": 10.0, "waste_pass": True,
            "scrap_rate": 33.33, "scrap_threshold": 30.0, "scrap_pass": False,
            "yield_pct": 66.67, "yield_threshold": 50.0, "yield_pass": True,
            "all_pass": False,
            "failures": ["Scrap rate 33.3% exceeds threshold 30%"],
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/threshold-check")
    assert resp.status_code == 200
    assert resp.json()["all_pass"] is False
    assert len(resp.json()["failures"]) == 1


def test_plan_threshold_check_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_threshold_check.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/threshold-check")
    assert resp.status_code == 404


def test_export_envelopes():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_envelopes.return_value = {
            "thresholds_overview": {"total_plans": 1},
            "envelopes_summary": {"total_materials": 1},
            "plan_checks": [{"plan_id": "p1", "plan_name": "Plan 1", "all_pass": True}],
        }
        resp = client.get("/api/v1/cutted-parts/export/envelopes")
    assert resp.status_code == 200
    assert "thresholds_overview" in resp.json()
    assert "envelopes_summary" in resp.json()
    assert len(resp.json()["plan_checks"]) == 1


# ---------------------------------------------------------------------------
# Alerts / Outliers endpoints (C40)
# ---------------------------------------------------------------------------


def test_alerts_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.alerts_overview.return_value = {
            "total_plans": 3,
            "critical_count": 1, "critical_plan_ids": ["p3"],
            "warning_count": 1, "warning_plan_ids": ["p2"],
            "healthy_count": 1,
        }
        resp = client.get("/api/v1/cutted-parts/alerts/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["critical_count"] == 1
    assert resp.json()["healthy_count"] == 1


def test_outliers_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.outliers_summary.return_value = {
            "total_plans": 4, "plans_with_waste_data": 4,
            "fleet_mean": 10.0, "fleet_std": 5.0,
            "outlier_threshold": 20.0,
            "outlier_count": 1, "outlier_plan_ids": ["p4"],
        }
        resp = client.get("/api/v1/cutted-parts/outliers/summary")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 4
    assert resp.json()["outlier_count"] == 1


def test_plan_alerts():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_alerts.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "total_cuts": 3, "ok_count": 2, "scrap_count": 1,
            "waste_pct": 18.0, "yield_pct": 66.67,
            "alert_count": 1,
            "alerts": [{"level": "critical", "metric": "waste_pct",
                        "value": 18.0, "threshold": 15.0,
                        "message": "Waste 18.0% critically exceeds 15% limit"}],
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/alerts")
    assert resp.status_code == 200
    assert resp.json()["alert_count"] == 1
    assert resp.json()["alerts"][0]["level"] == "critical"


def test_plan_alerts_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_alerts.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/alerts")
    assert resp.status_code == 404


def test_export_outliers():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_outliers.return_value = {
            "alerts_overview": {"total_plans": 1},
            "outliers_summary": {"total_plans": 1},
            "plan_alerts": [{"plan_id": "p1", "plan_name": "Plan 1", "alert_count": 0}],
        }
        resp = client.get("/api/v1/cutted-parts/export/outliers")
    assert resp.status_code == 200
    assert "alerts_overview" in resp.json()
    assert "outliers_summary" in resp.json()
    assert len(resp.json()["plan_alerts"]) == 1


# ---------------------------------------------------------------------------
# Throughput / Cadence endpoints (C43)
# ---------------------------------------------------------------------------


def test_throughput_overview():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.throughput_overview.return_value = {
            "total_plans": 3, "total_cuts": 10,
            "avg_cuts_per_plan": 3.33,
            "max_cuts_plan_id": "p1", "max_cuts_count": 5,
            "min_cuts_plan_id": "p3", "min_cuts_count": 1,
            "fleet_yield_pct": 80.0,
        }
        resp = client.get("/api/v1/cutted-parts/throughput/overview")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["total_cuts"] == 10
    assert resp.json()["fleet_yield_pct"] == 80.0


def test_cadence_summary():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.cadence_summary.return_value = {
            "total_plans": 3,
            "high_cadence_count": 1, "high_cadence_plan_ids": ["p1"],
            "medium_cadence_count": 1, "medium_cadence_plan_ids": ["p2"],
            "low_cadence_count": 1, "low_cadence_plan_ids": ["p3"],
        }
        resp = client.get("/api/v1/cutted-parts/cadence/summary")
    assert resp.status_code == 200
    assert resp.json()["total_plans"] == 3
    assert resp.json()["high_cadence_count"] == 1


def test_plan_cadence():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_cadence.return_value = {
            "plan_id": "plan-1", "plan_name": "Test Plan", "state": "draft",
            "total_cuts": 5, "ok_count": 4, "scrap_count": 1, "rework_count": 0,
            "yield_pct": 80.0, "cadence_tier": "high",
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/cadence")
    assert resp.status_code == 200
    assert resp.json()["cadence_tier"] == "high"
    assert resp.json()["yield_pct"] == 80.0


def test_plan_cadence_not_found_404():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_cadence.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/cadence")
    assert resp.status_code == 404


def test_export_cadence():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_cadence.return_value = {
            "throughput_overview": {"total_plans": 1},
            "cadence_summary": {"total_plans": 1},
            "plan_cadences": [{"plan_id": "p1", "plan_name": "Plan 1", "cadence_tier": "low"}],
        }
        resp = client.get("/api/v1/cutted-parts/export/cadence")
    assert resp.status_code == 200
    assert "throughput_overview" in resp.json()
    assert "cadence_summary" in resp.json()
    assert len(resp.json()["plan_cadences"]) == 1


# ---------------------------------------------------------------------------
# Saturation / Bottlenecks endpoints (C46)
# ---------------------------------------------------------------------------


def test_saturation_overview_c46():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.saturation_overview.return_value = {
            "total_plans": 3,
            "total_cuts": 11,
            "avg_cut_density": 3.67,
            "high_saturation_count": 2,
            "high_saturation_plan_ids": ["p1", "p2"],
            "bucket_counts": {"low": 1, "medium": 0, "high": 1, "critical": 1},
        }
        resp = client.get("/api/v1/cutted-parts/saturation/overview")
    assert resp.status_code == 200
    assert resp.json()["high_saturation_count"] == 2
    assert resp.json()["bucket_counts"]["critical"] == 1


def test_bottlenecks_summary_c46():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.bottlenecks_summary.return_value = {
            "total_plans": 3,
            "constrained_material_count": 1,
            "constrained_material_ids": ["mat-1"],
            "congested_plan_count": 2,
            "congested_plan_ids": ["p1", "p2"],
            "blocked_plan_count": 2,
            "blocked_plan_ids": ["p1", "p2"],
            "blocker_breakdown": {"scrap_heavy": 2},
        }
        resp = client.get("/api/v1/cutted-parts/bottlenecks/summary")
    assert resp.status_code == 200
    assert resp.json()["constrained_material_count"] == 1
    assert resp.json()["blocked_plan_count"] == 2


def test_plan_bottlenecks_c46():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_bottlenecks.return_value = {
            "plan_id": "plan-1",
            "plan_name": "Hot Plan",
            "state": "draft",
            "material_id": "mat-1",
            "material_quantity": 1.0,
            "total_cuts": 6,
            "ok_count": 3,
            "scrap_count": 2,
            "rework_count": 1,
            "waste_pct": 18.0,
            "yield_pct": 50.0,
            "scrap_rate_pct": 33.33,
            "cut_density": 6.0,
            "saturation_bucket": "critical",
            "material_stress": "high",
            "bottlenecks": ["saturation_critical", "scrap_heavy"],
        }
        resp = client.get("/api/v1/cutted-parts/plans/plan-1/bottlenecks")
    assert resp.status_code == 200
    assert resp.json()["saturation_bucket"] == "critical"
    assert resp.json()["material_stress"] == "high"


def test_plan_bottlenecks_not_found_404_c46():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.plan_bottlenecks.side_effect = ValueError("Plan 'x' not found")
        resp = client.get("/api/v1/cutted-parts/plans/x/bottlenecks")
    assert resp.status_code == 404


def test_export_bottlenecks_c46():
    client, db = _client_with_user()
    with patch("yuantus.meta_engine.web.cutted_parts_router.CuttedPartsService") as svc_cls:
        service = svc_cls.return_value
        service.export_bottlenecks.return_value = {
            "saturation_overview": {"total_plans": 1},
            "bottlenecks_summary": {"blocked_plan_count": 1},
            "plan_bottlenecks": [{"plan_id": "p1", "material_stress": "medium"}],
        }
        resp = client.get("/api/v1/cutted-parts/export/bottlenecks")
    assert resp.status_code == 200
    assert "saturation_overview" in resp.json()
    assert "bottlenecks_summary" in resp.json()
    assert len(resp.json()["plan_bottlenecks"]) == 1
