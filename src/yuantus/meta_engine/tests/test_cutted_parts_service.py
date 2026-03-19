"""Tests for C19 – Cutted-parts domain service layer."""

from unittest.mock import MagicMock
import pytest

from yuantus.meta_engine.cutted_parts.models import (
    CutPlan,
    CutPlanState,
    CutResult,
    CutResultStatus,
    MaterialType,
    RawMaterial,
)
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


class _MockQuery:
    """Minimal query mock that supports filter + order_by + all()."""

    def __init__(self, items):
        self._items = list(items)

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self._items)


def _mock_session():
    session = MagicMock()
    _store = {}

    def mock_add(obj):
        _store[obj.id] = obj

    def mock_get(model, obj_id):
        obj = _store.get(obj_id)
        if obj and isinstance(obj, model):
            return obj
        return None

    def mock_flush():
        pass

    def mock_query(model):
        return _MockQuery(
            obj for obj in _store.values() if isinstance(obj, model)
        )

    session.add.side_effect = mock_add
    session.get.side_effect = mock_get
    session.flush.side_effect = mock_flush
    session.query.side_effect = mock_query
    session._store = _store
    return session


# ---------------------------------------------------------------------------
# Material CRUD
# ---------------------------------------------------------------------------


class TestMaterialCRUD:

    def test_create_material_defaults(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        mat = svc.create_material(name="Steel Sheet 1.5mm")
        assert mat.id
        assert mat.name == "Steel Sheet 1.5mm"
        assert mat.material_type == MaterialType.SHEET.value
        assert mat.dimension_unit == "mm"
        assert mat.weight_unit == "kg"
        assert mat.stock_quantity == 0.0

    def test_create_material_with_dimensions(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        mat = svc.create_material(
            name="Aluminum Bar 20mm",
            material_type="bar",
            grade="6061-T6",
            length=3000.0,
            width=20.0,
            thickness=20.0,
            weight_per_unit=3.24,
            stock_quantity=50.0,
            cost_per_unit=12.50,
        )
        assert mat.material_type == "bar"
        assert mat.grade == "6061-T6"
        assert mat.length == 3000.0
        assert mat.stock_quantity == 50.0

    def test_create_material_invalid_type_raises(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        with pytest.raises(ValueError, match="Invalid material_type"):
            svc.create_material(name="Bad", material_type="invalid")

    def test_list_materials(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        svc.create_material(name="Mat A")
        svc.create_material(name="Mat B")
        materials = svc.list_materials()
        assert len(materials) == 2


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------


class TestPlanCRUD:

    def test_create_plan_defaults(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Cutting Job #1")
        assert plan.id
        assert plan.name == "Cutting Job #1"
        assert plan.state == CutPlanState.DRAFT.value
        assert plan.material_quantity == 1.0

    def test_create_plan_with_material(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        mat = svc.create_material(name="Steel Sheet")
        plan = svc.create_plan(
            name="Job #2",
            material_id=mat.id,
            material_quantity=5.0,
            description="Five sheets",
        )
        assert plan.material_id == mat.id
        assert plan.material_quantity == 5.0
        assert plan.description == "Five sheets"

    def test_get_plan(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Test Plan")
        found = svc.get_plan(plan.id)
        assert found is not None
        assert found.name == "Test Plan"

    def test_get_plan_not_found(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        assert svc.get_plan("nonexistent") is None

    def test_list_plans(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        svc.create_plan(name="Plan A")
        svc.create_plan(name="Plan B")
        plans = svc.list_plans()
        assert len(plans) == 2

    def test_update_plan(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Original")
        updated = svc.update_plan(plan.id, name="Renamed", description="Updated desc")
        assert updated.name == "Renamed"
        assert updated.description == "Updated desc"

    def test_update_plan_not_found(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        assert svc.update_plan("nonexistent", name="X") is None


# ---------------------------------------------------------------------------
# Plan state transitions
# ---------------------------------------------------------------------------


class TestPlanState:

    def test_draft_to_confirmed(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        result = svc.transition_plan_state(plan.id, CutPlanState.CONFIRMED.value)
        assert result.state == CutPlanState.CONFIRMED.value

    def test_confirmed_to_in_progress(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        svc.transition_plan_state(plan.id, CutPlanState.CONFIRMED.value)
        result = svc.transition_plan_state(plan.id, CutPlanState.IN_PROGRESS.value)
        assert result.state == CutPlanState.IN_PROGRESS.value

    def test_in_progress_to_completed(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        svc.transition_plan_state(plan.id, CutPlanState.CONFIRMED.value)
        svc.transition_plan_state(plan.id, CutPlanState.IN_PROGRESS.value)
        result = svc.transition_plan_state(plan.id, CutPlanState.COMPLETED.value)
        assert result.state == CutPlanState.COMPLETED.value

    def test_cancel_from_draft(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        result = svc.transition_plan_state(plan.id, CutPlanState.CANCELLED.value)
        assert result.state == CutPlanState.CANCELLED.value

    def test_invalid_transition_raises(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_plan_state(plan.id, CutPlanState.IN_PROGRESS.value)

    def test_completed_is_terminal(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        svc.transition_plan_state(plan.id, CutPlanState.CONFIRMED.value)
        svc.transition_plan_state(plan.id, CutPlanState.IN_PROGRESS.value)
        svc.transition_plan_state(plan.id, CutPlanState.COMPLETED.value)
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_plan_state(plan.id, CutPlanState.DRAFT.value)

    def test_transition_not_found_raises(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.transition_plan_state("nonexistent", CutPlanState.CONFIRMED.value)


# ---------------------------------------------------------------------------
# Cut results
# ---------------------------------------------------------------------------


class TestCutResults:

    def test_add_cut_default_status(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        cut = svc.add_cut(plan.id, length=100.0, width=50.0, quantity=2.0)
        assert cut.id
        assert cut.plan_id == plan.id
        assert cut.status == CutResultStatus.OK.value
        assert cut.length == 100.0

    def test_add_cut_scrap(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        cut = svc.add_cut(
            plan.id, status="scrap", scrap_weight=0.5, note="Edge defect"
        )
        assert cut.status == "scrap"
        assert cut.scrap_weight == 0.5
        assert cut.note == "Edge defect"

    def test_add_cut_invalid_status_raises(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        with pytest.raises(ValueError, match="Invalid status"):
            svc.add_cut(plan.id, status="invalid")

    def test_add_cut_plan_not_found_raises(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.add_cut("nonexistent")

    def test_list_cuts(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan")
        svc.add_cut(plan.id, length=100.0)
        svc.add_cut(plan.id, length=200.0)
        cuts = svc.list_cuts(plan.id)
        assert len(cuts) == 2


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestPlanSummary:

    def test_plan_summary(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Summary Plan")
        plan.waste_pct = 5.0
        svc.add_cut(plan.id, length=100.0, quantity=3.0, status="ok")
        svc.add_cut(plan.id, length=50.0, quantity=1.0, status="scrap", scrap_weight=0.8)
        svc.add_cut(plan.id, length=75.0, quantity=2.0, status="rework")

        summary = svc.plan_summary(plan.id)
        assert summary["plan_id"] == plan.id
        assert summary["name"] == "Summary Plan"
        assert summary["total_cuts"] == 3
        assert summary["total_quantity"] == 6.0
        assert summary["by_status"]["ok"] == 1
        assert summary["by_status"]["scrap"] == 1
        assert summary["by_status"]["rework"] == 1
        assert summary["total_scrap_weight"] == 0.8
        assert summary["waste_pct"] == 5.0

    def test_plan_summary_not_found_raises(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.plan_summary("nonexistent")


# ---------------------------------------------------------------------------
# Analytics (C22)
# ---------------------------------------------------------------------------


class TestAnalytics:

    def test_overview(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Plan A")
        plan.total_parts = 10
        plan.ok_count = 8
        plan.scrap_count = 1
        plan.rework_count = 1
        svc.create_material(name="Steel")

        result = svc.overview()
        assert result["total_plans"] == 1
        assert result["plans_by_state"]["draft"] == 1
        assert result["total_materials"] == 1
        assert result["total_parts"] == 10
        assert result["total_ok"] == 8
        assert result["total_scrap"] == 1
        assert result["total_rework"] == 1

    def test_overview_empty(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        result = svc.overview()
        assert result["total_plans"] == 0
        assert result["total_materials"] == 0
        assert result["plans_by_state"] == {}

    def test_material_analytics(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        svc.create_material(
            name="Steel A", material_type="sheet",
            stock_quantity=100.0, cost_per_unit=10.0,
        )
        svc.create_material(
            name="Aluminum B", material_type="bar",
            stock_quantity=50.0, cost_per_unit=20.0,
        )

        result = svc.material_analytics()
        assert result["total_materials"] == 2
        assert result["active_count"] == 2
        assert result["by_type"]["sheet"] == 1
        assert result["by_type"]["bar"] == 1
        assert result["total_stock_quantity"] == 150.0
        assert result["total_cost_value"] == 2000.0  # 100*10 + 50*20

    def test_waste_summary(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Waste Plan")
        plan.waste_pct = 8.5
        svc.add_cut(plan.id, status="ok", quantity=3.0)
        svc.add_cut(plan.id, status="scrap", quantity=1.0, scrap_weight=0.5)
        svc.add_cut(plan.id, status="rework", quantity=1.0)

        result = svc.waste_summary(plan.id)
        assert result["plan_id"] == plan.id
        assert result["total_cuts"] == 3
        assert result["ok_count"] == 1
        assert result["scrap_count"] == 1
        assert result["rework_count"] == 1
        assert result["total_scrap_weight"] == 0.5
        assert result["waste_pct"] == 8.5
        assert result["utilization_pct"] == 33.33  # 1/3 * 100

    def test_waste_summary_not_found(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.waste_summary("nonexistent")

    def test_waste_summary_empty_plan(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Empty")
        result = svc.waste_summary(plan.id)
        assert result["total_cuts"] == 0
        assert result["utilization_pct"] is None

    def test_export_overview(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        svc.create_plan(name="P1")
        svc.create_material(name="M1")
        result = svc.export_overview()
        assert "overview" in result
        assert "material_analytics" in result
        assert result["overview"]["total_plans"] == 1
        assert result["material_analytics"]["total_materials"] == 1

    def test_export_waste(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="Export Plan")
        plan.waste_pct = 5.0
        svc.add_cut(plan.id, status="ok")
        svc.add_cut(plan.id, status="scrap", scrap_weight=0.3)

        result = svc.export_waste()
        assert result["total_plans"] == 1
        assert len(result["plans"]) == 1
        p = result["plans"][0]
        assert p["plan_id"] == plan.id
        assert p["total_cuts"] == 2
        assert p["scrap_count"] == 1
        assert p["total_scrap_weight"] == 0.3

    def test_export_waste_empty(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        result = svc.export_waste()
        assert result["total_plans"] == 0
        assert result["plans"] == []


# ---------------------------------------------------------------------------
# Cost / Utilization (C25)
# ---------------------------------------------------------------------------


class TestCosting:

    def test_utilization_overview(self):
        session = _mock_session()
        svc = CuttedPartsService(session)

        p1 = svc.create_plan(name="Plan A")
        p1.total_parts = 10
        p1.ok_count = 9  # 90% → high

        p2 = svc.create_plan(name="Plan B")
        p2.total_parts = 10
        p2.ok_count = 6  # 60% → medium

        p3 = svc.create_plan(name="Plan C")
        p3.total_parts = 10
        p3.ok_count = 3  # 30% → low

        result = svc.utilization_overview()
        assert result["total_plans"] == 3
        assert result["plans_with_data"] == 3
        assert result["avg_utilization_pct"] == 60.0  # (90+60+30)/3
        assert result["high_utilization"] == 1
        assert result["medium_utilization"] == 1
        assert result["low_utilization"] == 1

    def test_utilization_overview_empty(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        result = svc.utilization_overview()
        assert result["total_plans"] == 0
        assert result["plans_with_data"] == 0
        assert result["avg_utilization_pct"] is None

    def test_utilization_overview_no_data_plans(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        p = svc.create_plan(name="Empty Plan")
        p.total_parts = 0
        p.ok_count = 0

        result = svc.utilization_overview()
        assert result["total_plans"] == 1
        assert result["plans_with_data"] == 0
        assert result["avg_utilization_pct"] is None

    def test_material_utilization(self):
        session = _mock_session()
        svc = CuttedPartsService(session)

        mat = svc.create_material(
            name="Steel Sheet", stock_quantity=100.0, cost_per_unit=10.0,
        )
        p1 = svc.create_plan(
            name="Job 1", material_id=mat.id, material_quantity=30.0,
        )
        p2 = svc.create_plan(
            name="Job 2", material_id=mat.id, material_quantity=20.0,
        )

        result = svc.material_utilization()
        assert result["total_materials"] == 1
        assert result["total_stock"] == 100.0
        assert result["total_consumed"] == 50.0
        assert len(result["materials"]) == 1

        item = result["materials"][0]
        assert item["consumed_quantity"] == 50.0
        assert item["remaining_quantity"] == 50.0
        assert item["plan_count"] == 2
        assert item["consumption_pct"] == 50.0

    def test_material_utilization_no_plans(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        svc.create_material(name="Unused Steel", stock_quantity=200.0)

        result = svc.material_utilization()
        assert result["total_materials"] == 1
        assert result["total_consumed"] == 0.0
        item = result["materials"][0]
        assert item["consumed_quantity"] == 0.0
        assert item["remaining_quantity"] == 200.0
        assert item["plan_count"] == 0
        assert item["consumption_pct"] == 0.0

    def test_plan_cost_summary(self):
        session = _mock_session()
        svc = CuttedPartsService(session)

        mat = svc.create_material(
            name="Steel", stock_quantity=100.0, cost_per_unit=10.0,
        )
        plan = svc.create_plan(
            name="Cost Plan", material_id=mat.id, material_quantity=5.0,
        )
        svc.add_cut(plan.id, status="ok", quantity=1.0)
        svc.add_cut(plan.id, status="ok", quantity=1.0)
        svc.add_cut(plan.id, status="scrap", quantity=1.0, scrap_weight=0.3)

        result = svc.plan_cost_summary(plan.id)
        assert result["plan_id"] == plan.id
        assert result["material_name"] == "Steel"
        assert result["material_cost"] == 50.0  # 10 * 5
        assert result["total_cuts"] == 3
        assert result["ok_count"] == 2
        assert result["total_scrap_weight"] == 0.3
        assert result["cost_per_good_part"] == 25.0  # 50 / 2

    def test_plan_cost_summary_no_material(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        plan = svc.create_plan(name="No Material Plan")
        svc.add_cut(plan.id, status="ok")

        result = svc.plan_cost_summary(plan.id)
        assert result["material_cost"] is None
        assert result["material_name"] is None
        assert result["cost_per_good_part"] is None

    def test_plan_cost_summary_not_found(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.plan_cost_summary("nonexistent")

    def test_export_utilization(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        p = svc.create_plan(name="P1")
        p.total_parts = 10
        p.ok_count = 8
        svc.create_material(name="M1", stock_quantity=50.0)

        result = svc.export_utilization()
        assert "utilization_overview" in result
        assert "material_utilization" in result
        assert result["utilization_overview"]["total_plans"] == 1
        assert result["material_utilization"]["total_materials"] == 1

    def test_export_costs(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        mat = svc.create_material(
            name="Steel", stock_quantity=100.0, cost_per_unit=10.0,
        )
        plan = svc.create_plan(
            name="Plan", material_id=mat.id, material_quantity=3.0,
        )
        svc.add_cut(plan.id, status="ok")

        result = svc.export_costs()
        assert result["total_plans"] == 1
        assert result["total_material_cost"] == 30.0  # 10 * 3
        assert len(result["plans"]) == 1
        assert result["plans"][0]["material_cost"] == 30.0

    def test_export_costs_empty(self):
        session = _mock_session()
        svc = CuttedPartsService(session)
        result = svc.export_costs()
        assert result["total_plans"] == 0
        assert result["total_material_cost"] == 0.0
        assert result["plans"] == []
