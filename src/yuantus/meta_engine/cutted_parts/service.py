"""
CuttedPartsService – material management, cut plan lifecycle, cut results,
and summary/export for the cutted-parts domain.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.cutted_parts.models import (
    CutPlan,
    CutPlanState,
    CutResult,
    CutResultStatus,
    MaterialType,
    RawMaterial,
)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

_PLAN_TRANSITIONS: Dict[str, List[str]] = {
    CutPlanState.DRAFT.value: [
        CutPlanState.CONFIRMED.value,
        CutPlanState.CANCELLED.value,
    ],
    CutPlanState.CONFIRMED.value: [
        CutPlanState.IN_PROGRESS.value,
        CutPlanState.CANCELLED.value,
    ],
    CutPlanState.IN_PROGRESS.value: [
        CutPlanState.COMPLETED.value,
        CutPlanState.CANCELLED.value,
    ],
    CutPlanState.COMPLETED.value: [],
    CutPlanState.CANCELLED.value: [],
}


class CuttedPartsService:
    """Domain service for cutted-parts / cutting-plan management."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Raw materials
    # ------------------------------------------------------------------

    def create_material(
        self,
        *,
        name: str,
        material_type: str = MaterialType.SHEET.value,
        grade: Optional[str] = None,
        length: Optional[float] = None,
        width: Optional[float] = None,
        thickness: Optional[float] = None,
        dimension_unit: str = "mm",
        weight_per_unit: Optional[float] = None,
        weight_unit: str = "kg",
        stock_quantity: float = 0.0,
        cost_per_unit: Optional[float] = None,
        product_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[int] = None,
    ) -> RawMaterial:
        valid_types = {t.value for t in MaterialType}
        if material_type not in valid_types:
            raise ValueError(
                f"Invalid material_type '{material_type}'. "
                f"Must be one of: {sorted(valid_types)}"
            )

        mat = RawMaterial(
            id=str(uuid.uuid4()),
            name=name,
            material_type=material_type,
            grade=grade,
            length=length,
            width=width,
            thickness=thickness,
            dimension_unit=dimension_unit,
            weight_per_unit=weight_per_unit,
            weight_unit=weight_unit,
            stock_quantity=stock_quantity,
            cost_per_unit=cost_per_unit,
            product_id=product_id,
            is_active=True,
            properties=properties,
            created_by_id=created_by_id,
        )
        self.session.add(mat)
        self.session.flush()
        return mat

    def list_materials(
        self,
        *,
        material_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[RawMaterial]:
        q = self.session.query(RawMaterial)
        if material_type is not None:
            q = q.filter(RawMaterial.material_type == material_type)
        if is_active is not None:
            q = q.filter(RawMaterial.is_active == is_active)
        return q.order_by(RawMaterial.created_at.desc()).all()

    # ------------------------------------------------------------------
    # Cut plan CRUD
    # ------------------------------------------------------------------

    def create_plan(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        material_id: Optional[str] = None,
        material_quantity: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[int] = None,
    ) -> CutPlan:
        plan = CutPlan(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            state=CutPlanState.DRAFT.value,
            material_id=material_id,
            material_quantity=material_quantity,
            properties=properties,
            created_by_id=created_by_id,
        )
        self.session.add(plan)
        self.session.flush()
        return plan

    def get_plan(self, plan_id: str) -> Optional[CutPlan]:
        return self.session.get(CutPlan, plan_id)

    def list_plans(
        self,
        *,
        state: Optional[str] = None,
        material_id: Optional[str] = None,
    ) -> List[CutPlan]:
        q = self.session.query(CutPlan)
        if state is not None:
            q = q.filter(CutPlan.state == state)
        if material_id is not None:
            q = q.filter(CutPlan.material_id == material_id)
        return q.order_by(CutPlan.created_at.desc()).all()

    def update_plan(self, plan_id: str, **fields: Any) -> Optional[CutPlan]:
        plan = self.get_plan(plan_id)
        if plan is None:
            return None
        for key, value in fields.items():
            if hasattr(plan, key) and key not in (
                "id", "created_at", "created_by_id",
            ):
                setattr(plan, key, value)
        self.session.flush()
        return plan

    def transition_plan_state(
        self, plan_id: str, target_state: str
    ) -> CutPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        allowed = _PLAN_TRANSITIONS.get(plan.state, [])
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition plan from '{plan.state}' to "
                f"'{target_state}'. Allowed: {allowed}"
            )
        plan.state = target_state
        self.session.flush()
        return plan

    # ------------------------------------------------------------------
    # Cut results
    # ------------------------------------------------------------------

    def add_cut(
        self,
        plan_id: str,
        *,
        part_id: Optional[str] = None,
        length: Optional[float] = None,
        width: Optional[float] = None,
        quantity: float = 1.0,
        status: str = CutResultStatus.OK.value,
        scrap_weight: Optional[float] = None,
        note: Optional[str] = None,
    ) -> CutResult:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        valid_statuses = {s.value for s in CutResultStatus}
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Must be one of: {sorted(valid_statuses)}"
            )

        cut = CutResult(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            part_id=part_id,
            length=length,
            width=width,
            quantity=quantity,
            status=status,
            scrap_weight=scrap_weight,
            note=note,
        )
        self.session.add(cut)
        self.session.flush()
        return cut

    def list_cuts(self, plan_id: str) -> List[CutResult]:
        cuts = (
            self.session.query(CutResult)
            .filter(CutResult.plan_id == plan_id)
            .order_by(CutResult.created_at)
            .all()
        )
        return [cut for cut in cuts if cut.plan_id == plan_id]

    # ------------------------------------------------------------------
    # Summary / export
    # ------------------------------------------------------------------

    def plan_summary(self, plan_id: str) -> Dict[str, Any]:
        """Build a stock-usage / waste summary for downstream export."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan_id)

        by_status: Dict[str, int] = {}
        total_scrap = 0.0
        total_quantity = 0.0

        for c in cuts:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            total_quantity += (c.quantity or 0.0)
            if c.scrap_weight:
                total_scrap += c.scrap_weight

        return {
            "plan_id": plan.id,
            "name": plan.name,
            "state": plan.state,
            "material_id": plan.material_id,
            "material_quantity": plan.material_quantity,
            "total_cuts": len(cuts),
            "total_quantity": total_quantity,
            "by_status": by_status,
            "total_scrap_weight": total_scrap,
            "waste_pct": plan.waste_pct,
        }

    # ------------------------------------------------------------------
    # Analytics (C22)
    # ------------------------------------------------------------------

    def overview(self) -> Dict[str, Any]:
        """High-level overview: plan counts, state breakdown, totals."""
        plans = self.session.query(CutPlan).all()
        materials = self.session.query(RawMaterial).all()

        by_state: Dict[str, int] = {}
        total_parts = 0
        total_scrap = 0
        total_ok = 0
        total_rework = 0
        for p in plans:
            by_state[p.state] = by_state.get(p.state, 0) + 1
            total_parts += (p.total_parts or 0)
            total_ok += (p.ok_count or 0)
            total_scrap += (p.scrap_count or 0)
            total_rework += (p.rework_count or 0)

        return {
            "total_plans": len(plans),
            "plans_by_state": by_state,
            "total_materials": len(materials),
            "total_parts": total_parts,
            "total_ok": total_ok,
            "total_scrap": total_scrap,
            "total_rework": total_rework,
        }

    def material_analytics(self) -> Dict[str, Any]:
        """Material-level analytics: breakdown by type, stock, cost."""
        materials = self.session.query(RawMaterial).all()

        by_type: Dict[str, int] = {}
        total_stock = 0.0
        total_cost_value = 0.0
        active_count = 0

        for m in materials:
            by_type[m.material_type] = by_type.get(m.material_type, 0) + 1
            total_stock += (m.stock_quantity or 0.0)
            if m.cost_per_unit and m.stock_quantity:
                total_cost_value += m.cost_per_unit * m.stock_quantity
            if m.is_active:
                active_count += 1

        return {
            "total_materials": len(materials),
            "active_count": active_count,
            "by_type": by_type,
            "total_stock_quantity": total_stock,
            "total_cost_value": total_cost_value,
        }

    def waste_summary(self, plan_id: str) -> Dict[str, Any]:
        """Waste / utilization summary for a specific plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan_id)

        ok_count = 0
        scrap_count = 0
        rework_count = 0
        total_scrap_weight = 0.0
        total_quantity = 0.0

        for c in cuts:
            total_quantity += (c.quantity or 0.0)
            if c.status == CutResultStatus.OK.value:
                ok_count += 1
            elif c.status == CutResultStatus.SCRAP.value:
                scrap_count += 1
                total_scrap_weight += (c.scrap_weight or 0.0)
            elif c.status == CutResultStatus.REWORK.value:
                rework_count += 1

        utilization_pct = None
        if len(cuts) > 0:
            utilization_pct = round(ok_count / len(cuts) * 100, 2)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "total_cuts": len(cuts),
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "rework_count": rework_count,
            "total_quantity": total_quantity,
            "total_scrap_weight": total_scrap_weight,
            "waste_pct": plan.waste_pct,
            "utilization_pct": utilization_pct,
        }

    def export_overview(self) -> Dict[str, Any]:
        """Export-ready combined overview + material analytics."""
        return {
            "overview": self.overview(),
            "material_analytics": self.material_analytics(),
        }

    def export_waste(self) -> Dict[str, Any]:
        """Export-ready waste summary across all plans."""
        plans = self.session.query(CutPlan).all()
        plan_summaries = []
        for p in plans:
            cuts = self.list_cuts(p.id)
            scrap_weight = sum((c.scrap_weight or 0.0) for c in cuts)
            scrap_count = sum(
                1 for c in cuts if c.status == CutResultStatus.SCRAP.value
            )
            plan_summaries.append({
                "plan_id": p.id,
                "plan_name": p.name,
                "state": p.state,
                "total_cuts": len(cuts),
                "scrap_count": scrap_count,
                "total_scrap_weight": scrap_weight,
                "waste_pct": p.waste_pct,
            })
        return {
            "total_plans": len(plans),
            "plans": plan_summaries,
        }

    # ------------------------------------------------------------------
    # Cost / Utilization (C25)
    # ------------------------------------------------------------------

    def utilization_overview(self) -> Dict[str, Any]:
        """Fleet-wide utilization summary across all plans."""
        plans = self.session.query(CutPlan).all()

        plans_with_data = 0
        utilization_sum = 0.0
        high_util = 0   # >=80 %
        medium_util = 0  # 50-79 %
        low_util = 0     # <50 %

        for p in plans:
            total = p.total_parts or 0
            ok = p.ok_count or 0
            if total > 0:
                plans_with_data += 1
                util = ok / total * 100
                utilization_sum += util
                if util >= 80:
                    high_util += 1
                elif util >= 50:
                    medium_util += 1
                else:
                    low_util += 1

        avg_utilization = (
            round(utilization_sum / plans_with_data, 2)
            if plans_with_data > 0
            else None
        )

        return {
            "total_plans": len(plans),
            "plans_with_data": plans_with_data,
            "avg_utilization_pct": avg_utilization,
            "high_utilization": high_util,
            "medium_utilization": medium_util,
            "low_utilization": low_util,
        }

    def material_utilization(self) -> Dict[str, Any]:
        """Material consumption and remaining-stock analysis."""
        materials = self.session.query(RawMaterial).all()
        plans = self.session.query(CutPlan).all()

        consumed_map: Dict[str, float] = {}
        plan_count_map: Dict[str, int] = {}
        for p in plans:
            if p.material_id:
                consumed_map[p.material_id] = (
                    consumed_map.get(p.material_id, 0.0)
                    + (p.material_quantity or 0.0)
                )
                plan_count_map[p.material_id] = (
                    plan_count_map.get(p.material_id, 0) + 1
                )

        items: List[Dict[str, Any]] = []
        total_stock = 0.0
        total_consumed = 0.0

        for m in materials:
            consumed = consumed_map.get(m.id, 0.0)
            stock = m.stock_quantity or 0.0
            total_stock += stock
            total_consumed += consumed

            items.append({
                "material_id": m.id,
                "material_name": m.name,
                "material_type": m.material_type,
                "stock_quantity": stock,
                "consumed_quantity": consumed,
                "remaining_quantity": stock - consumed,
                "plan_count": plan_count_map.get(m.id, 0),
                "consumption_pct": (
                    round(consumed / stock * 100, 2) if stock > 0 else None
                ),
            })

        return {
            "total_materials": len(materials),
            "total_stock": total_stock,
            "total_consumed": total_consumed,
            "materials": items,
        }

    def plan_cost_summary(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan cost: material cost, waste cost, cost per good part."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        material_cost: Optional[float] = None
        material_name: Optional[str] = None
        cost_per_unit: Optional[float] = None

        if plan.material_id:
            mat = self.session.get(RawMaterial, plan.material_id)
            if mat:
                material_name = mat.name
                cost_per_unit = mat.cost_per_unit
                if mat.cost_per_unit is not None:
                    material_cost = mat.cost_per_unit * (
                        plan.material_quantity or 0.0
                    )

        cuts = self.list_cuts(plan_id)
        total_scrap_weight = sum((c.scrap_weight or 0.0) for c in cuts)
        ok_count = sum(
            1 for c in cuts if c.status == CutResultStatus.OK.value
        )

        cost_per_good_part: Optional[float] = None
        if material_cost is not None and ok_count > 0:
            cost_per_good_part = round(material_cost / ok_count, 2)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "material_id": plan.material_id,
            "material_name": material_name,
            "material_quantity": plan.material_quantity,
            "cost_per_unit": cost_per_unit,
            "material_cost": material_cost,
            "total_cuts": len(cuts),
            "ok_count": ok_count,
            "total_scrap_weight": total_scrap_weight,
            "cost_per_good_part": cost_per_good_part,
        }

    def export_utilization(self) -> Dict[str, Any]:
        """Export-ready combined utilization payload."""
        return {
            "utilization_overview": self.utilization_overview(),
            "material_utilization": self.material_utilization(),
        }

    def export_costs(self) -> Dict[str, Any]:
        """Export-ready cost payload across all plans."""
        plans = self.session.query(CutPlan).all()
        plan_costs = []
        total_material_cost = 0.0

        for p in plans:
            summary = self.plan_cost_summary(p.id)
            if summary["material_cost"] is not None:
                total_material_cost += summary["material_cost"]
            plan_costs.append(summary)

        return {
            "total_plans": len(plans),
            "total_material_cost": total_material_cost,
            "plans": plan_costs,
        }

    # ------------------------------------------------------------------
    # Templates / Scenarios (C28)
    # ------------------------------------------------------------------

    def template_overview(self) -> Dict[str, Any]:
        """Fleet-wide template metrics: plan counts as templates, active
        scenario (non-terminal) count, and default material breakdown."""
        plans = self.session.query(CutPlan).all()
        materials = self.session.query(RawMaterial).all()

        template_count = len(plans)
        active_scenarios = 0
        terminal = {CutPlanState.COMPLETED.value, CutPlanState.CANCELLED.value}
        material_breakdown: Dict[str, int] = {}

        for p in plans:
            if p.state not in terminal:
                active_scenarios += 1
            if p.material_id:
                material_breakdown[p.material_id] = (
                    material_breakdown.get(p.material_id, 0) + 1
                )

        # Resolve material names
        mat_name_map: Dict[str, str] = {m.id: m.name for m in materials}
        material_detail: List[Dict[str, Any]] = []
        for mid, count in material_breakdown.items():
            material_detail.append({
                "material_id": mid,
                "material_name": mat_name_map.get(mid, mid),
                "plan_count": count,
            })

        return {
            "template_count": template_count,
            "active_scenarios": active_scenarios,
            "completed_scenarios": sum(
                1 for p in plans if p.state == CutPlanState.COMPLETED.value
            ),
            "material_breakdown": material_detail,
        }

    def scenario_summary(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan scenario comparison: waste/cost deltas vs fleet average,
        best-known snapshot for the plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan_id)

        ok_count = sum(
            1 for c in cuts if c.status == CutResultStatus.OK.value
        )
        scrap_count = sum(
            1 for c in cuts if c.status == CutResultStatus.SCRAP.value
        )
        rework_count = sum(
            1 for c in cuts if c.status == CutResultStatus.REWORK.value
        )
        total_scrap_weight = sum((c.scrap_weight or 0.0) for c in cuts)

        # Compute fleet average waste_pct
        all_plans = self.session.query(CutPlan).all()
        waste_values = [
            p.waste_pct for p in all_plans if p.waste_pct is not None
        ]
        fleet_avg_waste = (
            round(sum(waste_values) / len(waste_values), 2)
            if waste_values
            else None
        )
        waste_delta = None
        if plan.waste_pct is not None and fleet_avg_waste is not None:
            waste_delta = round(plan.waste_pct - fleet_avg_waste, 2)

        # Material cost for this plan
        material_cost: Optional[float] = None
        if plan.material_id:
            mat = self.session.get(RawMaterial, plan.material_id)
            if mat and mat.cost_per_unit is not None:
                material_cost = mat.cost_per_unit * (
                    plan.material_quantity or 0.0
                )

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "total_cuts": len(cuts),
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "rework_count": rework_count,
            "total_scrap_weight": total_scrap_weight,
            "waste_pct": plan.waste_pct,
            "fleet_avg_waste_pct": fleet_avg_waste,
            "waste_delta": waste_delta,
            "material_cost": material_cost,
        }

    def material_templates(self) -> Dict[str, Any]:
        """Template grouping by material type and stock profile."""
        materials = self.session.query(RawMaterial).all()
        plans = self.session.query(CutPlan).all()

        plan_count_map: Dict[str, int] = {}
        for p in plans:
            if p.material_id:
                plan_count_map[p.material_id] = (
                    plan_count_map.get(p.material_id, 0) + 1
                )

        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for m in materials:
            entry = {
                "material_id": m.id,
                "material_name": m.name,
                "grade": m.grade,
                "stock_quantity": m.stock_quantity or 0.0,
                "cost_per_unit": m.cost_per_unit,
                "is_active": m.is_active,
                "plan_count": plan_count_map.get(m.id, 0),
            }
            by_type.setdefault(m.material_type, []).append(entry)

        return {
            "total_materials": len(materials),
            "by_type": by_type,
        }

    def export_scenarios(self) -> Dict[str, Any]:
        """Export-ready payload combining template overview and per-plan
        scenario summaries."""
        plans = self.session.query(CutPlan).all()
        scenario_summaries = []
        for p in plans:
            scenario_summaries.append(self.scenario_summary(p.id))

        return {
            "template_overview": self.template_overview(),
            "material_templates": self.material_templates(),
            "scenarios": scenario_summaries,
        }

    # ------------------------------------------------------------------
    # Benchmark / Quote (C31)
    # ------------------------------------------------------------------

    def benchmark_overview(self) -> Dict[str, Any]:
        """Fleet-wide benchmark: plan counts, cost/waste ranges, best plan."""
        plans = self.session.query(CutPlan).all()

        completed = [
            p for p in plans if p.state == CutPlanState.COMPLETED.value
        ]
        with_waste = [p for p in plans if p.waste_pct is not None]

        waste_values = [p.waste_pct for p in with_waste]
        min_waste = min(waste_values) if waste_values else None
        max_waste = max(waste_values) if waste_values else None
        avg_waste = (
            round(sum(waste_values) / len(waste_values), 2)
            if waste_values
            else None
        )

        # Best plan = lowest waste_pct among those with data
        best_plan_id: Optional[str] = None
        best_plan_name: Optional[str] = None
        if with_waste:
            best = min(with_waste, key=lambda p: p.waste_pct)
            best_plan_id = best.id
            best_plan_name = best.name

        # Cost range across plans with material
        cost_values: List[float] = []
        for p in plans:
            if p.material_id:
                mat = self.session.get(RawMaterial, p.material_id)
                if mat and mat.cost_per_unit is not None:
                    cost_values.append(
                        mat.cost_per_unit * (p.material_quantity or 0.0)
                    )

        return {
            "total_plans": len(plans),
            "completed_plans": len(completed),
            "plans_with_waste_data": len(with_waste),
            "min_waste_pct": min_waste,
            "max_waste_pct": max_waste,
            "avg_waste_pct": avg_waste,
            "best_plan_id": best_plan_id,
            "best_plan_name": best_plan_name,
            "min_material_cost": min(cost_values) if cost_values else None,
            "max_material_cost": max(cost_values) if cost_values else None,
        }

    def quote_summary(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan quote-ready summary: material, cost, waste, yield."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan_id)
        ok_count = sum(
            1 for c in cuts if c.status == CutResultStatus.OK.value
        )
        scrap_count = sum(
            1 for c in cuts if c.status == CutResultStatus.SCRAP.value
        )
        total_scrap_weight = sum((c.scrap_weight or 0.0) for c in cuts)

        # Material cost
        material_cost: Optional[float] = None
        material_name: Optional[str] = None
        cost_per_unit: Optional[float] = None
        if plan.material_id:
            mat = self.session.get(RawMaterial, plan.material_id)
            if mat:
                material_name = mat.name
                cost_per_unit = mat.cost_per_unit
                if mat.cost_per_unit is not None:
                    material_cost = mat.cost_per_unit * (
                        plan.material_quantity or 0.0
                    )

        cost_per_good_part: Optional[float] = None
        if material_cost is not None and ok_count > 0:
            cost_per_good_part = round(material_cost / ok_count, 2)

        yield_pct: Optional[float] = None
        if len(cuts) > 0:
            yield_pct = round(ok_count / len(cuts) * 100, 2)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "material_name": material_name,
            "material_quantity": plan.material_quantity,
            "cost_per_unit": cost_per_unit,
            "material_cost": material_cost,
            "total_cuts": len(cuts),
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "total_scrap_weight": total_scrap_weight,
            "waste_pct": plan.waste_pct,
            "yield_pct": yield_pct,
            "cost_per_good_part": cost_per_good_part,
        }

    def material_benchmarks(self) -> Dict[str, Any]:
        """Benchmark aggregation by material: avg waste, plan count, cost."""
        materials = self.session.query(RawMaterial).all()
        plans = self.session.query(CutPlan).all()

        # Group plans by material_id
        plans_by_mat: Dict[str, List[CutPlan]] = {}
        for p in plans:
            if p.material_id:
                plans_by_mat.setdefault(p.material_id, []).append(p)

        benchmarks: List[Dict[str, Any]] = []
        for m in materials:
            mat_plans = plans_by_mat.get(m.id, [])
            waste_vals = [
                p.waste_pct for p in mat_plans if p.waste_pct is not None
            ]
            avg_waste = (
                round(sum(waste_vals) / len(waste_vals), 2)
                if waste_vals
                else None
            )
            total_cost = None
            if m.cost_per_unit is not None:
                total_cost = sum(
                    m.cost_per_unit * (p.material_quantity or 0.0)
                    for p in mat_plans
                )

            benchmarks.append({
                "material_id": m.id,
                "material_name": m.name,
                "material_type": m.material_type,
                "plan_count": len(mat_plans),
                "avg_waste_pct": avg_waste,
                "total_material_cost": total_cost,
                "stock_quantity": m.stock_quantity or 0.0,
                "cost_per_unit": m.cost_per_unit,
            })

        return {
            "total_materials": len(materials),
            "benchmarks": benchmarks,
        }

    def export_quotes(self) -> Dict[str, Any]:
        """Export-ready payload combining benchmark overview and per-plan
        quote summaries."""
        plans = self.session.query(CutPlan).all()
        quotes = []
        for p in plans:
            quotes.append(self.quote_summary(p.id))

        return {
            "benchmark_overview": self.benchmark_overview(),
            "material_benchmarks": self.material_benchmarks(),
            "quotes": quotes,
        }

    # ------------------------------------------------------------------
    # Variance / Recommendations (C34)
    # ------------------------------------------------------------------

    def variance_overview(self) -> Dict[str, Any]:
        """Fleet-wide variance analysis: waste spread, cost deviation,
        outlier identification across all plans."""
        plans = self.session.query(CutPlan).all()

        waste_values = [
            p.waste_pct for p in plans if p.waste_pct is not None
        ]

        waste_mean: Optional[float] = None
        waste_std: Optional[float] = None
        waste_range: Optional[float] = None
        if waste_values:
            waste_mean = round(sum(waste_values) / len(waste_values), 2)
            variance = sum(
                (v - waste_mean) ** 2 for v in waste_values
            ) / len(waste_values)
            waste_std = round(variance ** 0.5, 2)
            waste_range = round(max(waste_values) - min(waste_values), 2)

        # Cost variance
        cost_values: List[float] = []
        for p in plans:
            if p.material_id:
                mat = self.session.get(RawMaterial, p.material_id)
                if mat and mat.cost_per_unit is not None:
                    cost_values.append(
                        mat.cost_per_unit * (p.material_quantity or 0.0)
                    )

        cost_mean: Optional[float] = None
        cost_std: Optional[float] = None
        if cost_values:
            cost_mean = round(sum(cost_values) / len(cost_values), 2)
            c_var = sum(
                (v - cost_mean) ** 2 for v in cost_values
            ) / len(cost_values)
            cost_std = round(c_var ** 0.5, 2)

        # Outliers: plans with waste > mean + 1 std
        outlier_ids: List[str] = []
        if waste_mean is not None and waste_std is not None and waste_std > 0:
            threshold = waste_mean + waste_std
            for p in plans:
                if p.waste_pct is not None and p.waste_pct > threshold:
                    outlier_ids.append(p.id)

        return {
            "total_plans": len(plans),
            "plans_with_waste_data": len(waste_values),
            "waste_mean": waste_mean,
            "waste_std": waste_std,
            "waste_range": waste_range,
            "cost_mean": cost_mean,
            "cost_std": cost_std,
            "outlier_plan_ids": outlier_ids,
            "outlier_count": len(outlier_ids),
        }

    def plan_recommendations(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan recommendations based on waste/cost/utilization vs fleet."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan_id)
        ok_count = sum(
            1 for c in cuts if c.status == CutResultStatus.OK.value
        )
        scrap_count = sum(
            1 for c in cuts if c.status == CutResultStatus.SCRAP.value
        )
        total_scrap_weight = sum((c.scrap_weight or 0.0) for c in cuts)

        # Fleet averages
        all_plans = self.session.query(CutPlan).all()
        waste_values = [
            p.waste_pct for p in all_plans if p.waste_pct is not None
        ]
        fleet_avg_waste = (
            round(sum(waste_values) / len(waste_values), 2)
            if waste_values
            else None
        )

        # Recommendations based on metrics
        recommendations: List[str] = []
        severity: str = "ok"

        if plan.waste_pct is not None and fleet_avg_waste is not None:
            if plan.waste_pct > fleet_avg_waste * 1.5:
                recommendations.append(
                    "Waste significantly above fleet average — review cutting patterns"
                )
                severity = "high"
            elif plan.waste_pct > fleet_avg_waste:
                recommendations.append(
                    "Waste above fleet average — consider material optimization"
                )
                if severity == "ok":
                    severity = "medium"

        if len(cuts) > 0 and scrap_count / len(cuts) > 0.3:
            recommendations.append(
                "Scrap rate exceeds 30% — inspect tooling or material quality"
            )
            severity = "high"

        if len(cuts) > 0 and ok_count / len(cuts) < 0.5:
            recommendations.append(
                "Yield below 50% — review process parameters"
            )
            if severity == "ok":
                severity = "medium"

        yield_pct: Optional[float] = None
        if len(cuts) > 0:
            yield_pct = round(ok_count / len(cuts) * 100, 2)

        waste_delta: Optional[float] = None
        if plan.waste_pct is not None and fleet_avg_waste is not None:
            waste_delta = round(plan.waste_pct - fleet_avg_waste, 2)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "total_cuts": len(cuts),
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "total_scrap_weight": total_scrap_weight,
            "waste_pct": plan.waste_pct,
            "fleet_avg_waste_pct": fleet_avg_waste,
            "waste_delta": waste_delta,
            "yield_pct": yield_pct,
            "severity": severity,
            "recommendations": recommendations,
        }

    def material_variance(self) -> Dict[str, Any]:
        """Variance analysis by material: waste spread, cost deviation,
        plan-count distribution."""
        materials = self.session.query(RawMaterial).all()
        plans = self.session.query(CutPlan).all()

        plans_by_mat: Dict[str, List[CutPlan]] = {}
        for p in plans:
            if p.material_id:
                plans_by_mat.setdefault(p.material_id, []).append(p)

        items: List[Dict[str, Any]] = []
        for m in materials:
            mat_plans = plans_by_mat.get(m.id, [])
            waste_vals = [
                p.waste_pct for p in mat_plans if p.waste_pct is not None
            ]

            waste_mean: Optional[float] = None
            waste_std: Optional[float] = None
            if waste_vals:
                waste_mean = round(
                    sum(waste_vals) / len(waste_vals), 2
                )
                var = sum(
                    (v - waste_mean) ** 2 for v in waste_vals
                ) / len(waste_vals)
                waste_std = round(var ** 0.5, 2)

            total_cost: Optional[float] = None
            if m.cost_per_unit is not None:
                total_cost = sum(
                    m.cost_per_unit * (p.material_quantity or 0.0)
                    for p in mat_plans
                )

            items.append({
                "material_id": m.id,
                "material_name": m.name,
                "material_type": m.material_type,
                "plan_count": len(mat_plans),
                "waste_mean": waste_mean,
                "waste_std": waste_std,
                "total_material_cost": total_cost,
                "stock_quantity": m.stock_quantity or 0.0,
            })

        return {
            "total_materials": len(materials),
            "materials": items,
        }

    def export_recommendations(self) -> Dict[str, Any]:
        """Export-ready payload combining variance overview, material variance,
        and per-plan recommendations."""
        plans = self.session.query(CutPlan).all()
        plan_recs = []
        for p in plans:
            plan_recs.append(self.plan_recommendations(p.id))

        return {
            "variance_overview": self.variance_overview(),
            "material_variance": self.material_variance(),
            "recommendations": plan_recs,
        }

    # ------------------------------------------------------------------
    # Thresholds / Envelopes helpers (C37)
    # ------------------------------------------------------------------

    def thresholds_overview(self) -> Dict[str, Any]:
        """Fleet-wide threshold hit-rate summary.

        Defines waste/scrap/yield thresholds and reports how many plans
        exceed them.
        """
        plans = self.session.query(CutPlan).all()
        waste_threshold = 10.0   # waste_pct above this is a breach
        scrap_threshold = 0.30   # scrap rate above 30 %
        yield_threshold = 50.0   # yield below 50 % is a breach

        waste_breaches: list[str] = []
        scrap_breaches: list[str] = []
        yield_breaches: list[str] = []

        for p in plans:
            cuts = self.list_cuts(p.id)
            total = len(cuts)

            if (p.waste_pct or 0) > waste_threshold:
                waste_breaches.append(p.id)

            if total > 0:
                scrap_count = sum(1 for c in cuts if c.status == "scrap")
                ok_count = sum(1 for c in cuts if c.status == "ok")
                scrap_rate = scrap_count / total
                yield_pct = (ok_count / total) * 100.0

                if scrap_rate > scrap_threshold:
                    scrap_breaches.append(p.id)
                if yield_pct < yield_threshold:
                    yield_breaches.append(p.id)

        return {
            "total_plans": len(plans),
            "waste_threshold": waste_threshold,
            "scrap_threshold": scrap_threshold,
            "yield_threshold": yield_threshold,
            "waste_breach_count": len(waste_breaches),
            "waste_breach_plan_ids": waste_breaches,
            "scrap_breach_count": len(scrap_breaches),
            "scrap_breach_plan_ids": scrap_breaches,
            "yield_breach_count": len(yield_breaches),
            "yield_breach_plan_ids": yield_breaches,
        }

    def envelopes_summary(self) -> Dict[str, Any]:
        """Material and plan envelope summary.

        For each material, computes the waste envelope (min/max waste_pct
        across plans) and whether the material is within acceptable bounds.
        """
        materials = self.session.query(RawMaterial).all()
        envelope_limit = 15.0  # max acceptable waste_pct

        items: list[dict] = []
        within_count = 0
        exceeded_count = 0

        for m in materials:
            mat_plans = [
                p for p in self.session.query(CutPlan).all()
                if p.material_id == m.id
            ]
            waste_values = [p.waste_pct for p in mat_plans if p.waste_pct is not None]

            if waste_values:
                env_min = min(waste_values)
                env_max = max(waste_values)
                within = env_max <= envelope_limit
            else:
                env_min = None
                env_max = None
                within = True  # no data → no breach

            if within:
                within_count += 1
            else:
                exceeded_count += 1

            items.append({
                "material_id": m.id,
                "material_name": m.name,
                "plan_count": len(mat_plans),
                "envelope_min": env_min,
                "envelope_max": env_max,
                "envelope_limit": envelope_limit,
                "within_envelope": within,
            })

        return {
            "total_materials": len(materials),
            "envelope_limit": envelope_limit,
            "within_count": within_count,
            "exceeded_count": exceeded_count,
            "materials": items,
        }

    def plan_threshold_check(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan threshold detail — checks waste, scrap, yield against
        fleet-defined thresholds and reports pass/fail for each."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        waste_threshold = 10.0
        scrap_threshold = 0.30
        yield_threshold = 50.0

        cuts = self.list_cuts(plan.id)
        total = len(cuts)

        waste_pct = plan.waste_pct or 0.0
        waste_pass = waste_pct <= waste_threshold

        if total > 0:
            scrap_count = sum(1 for c in cuts if c.status == "scrap")
            ok_count = sum(1 for c in cuts if c.status == "ok")
            scrap_rate = scrap_count / total
            yield_pct = (ok_count / total) * 100.0
        else:
            scrap_count = 0
            ok_count = 0
            scrap_rate = 0.0
            yield_pct = None

        scrap_pass = scrap_rate <= scrap_threshold
        yield_pass = yield_pct is None or yield_pct >= yield_threshold

        all_pass = waste_pass and scrap_pass and yield_pass

        checks = []
        if not waste_pass:
            checks.append(f"Waste {waste_pct:.1f}% exceeds threshold {waste_threshold}%")
        if not scrap_pass:
            checks.append(f"Scrap rate {scrap_rate*100:.1f}% exceeds threshold {scrap_threshold*100:.0f}%")
        if not yield_pass:
            checks.append(f"Yield {yield_pct:.1f}% below threshold {yield_threshold}%")

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "total_cuts": total,
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "waste_pct": waste_pct,
            "waste_threshold": waste_threshold,
            "waste_pass": waste_pass,
            "scrap_rate": round(scrap_rate * 100, 2) if total > 0 else 0.0,
            "scrap_threshold": scrap_threshold * 100,
            "scrap_pass": scrap_pass,
            "yield_pct": yield_pct,
            "yield_threshold": yield_threshold,
            "yield_pass": yield_pass,
            "all_pass": all_pass,
            "failures": checks,
        }

    def export_envelopes(self) -> Dict[str, Any]:
        """Export-ready payload combining thresholds overview, envelopes
        summary, and per-plan threshold checks."""
        plans = self.session.query(CutPlan).all()
        plan_checks = []
        for p in plans:
            plan_checks.append(self.plan_threshold_check(p.id))

        return {
            "thresholds_overview": self.thresholds_overview(),
            "envelopes_summary": self.envelopes_summary(),
            "plan_checks": plan_checks,
        }

    # ------------------------------------------------------------------
    # Alerts / Outliers helpers (C40)
    # ------------------------------------------------------------------

    def alerts_overview(self) -> Dict[str, Any]:
        """Fleet-wide alert summary.

        Scans all plans for alert conditions:
        - waste_pct > 15 % → critical
        - waste_pct > 10 % → warning
        - scrap rate > 30 % → critical
        - yield < 50 % → warning
        """
        plans = self.session.query(CutPlan).all()

        critical_ids: list[str] = []
        warning_ids: list[str] = []

        for p in plans:
            is_critical = False
            is_warning = False

            if (p.waste_pct or 0) > 15.0:
                is_critical = True
            elif (p.waste_pct or 0) > 10.0:
                is_warning = True

            cuts = self.list_cuts(p.id)
            total = len(cuts)
            if total > 0:
                scrap_count = sum(1 for c in cuts if c.status == "scrap")
                ok_count = sum(1 for c in cuts if c.status == "ok")
                if scrap_count / total > 0.30:
                    is_critical = True
                if (ok_count / total) * 100 < 50.0:
                    is_warning = True

            if is_critical:
                critical_ids.append(p.id)
            elif is_warning:
                warning_ids.append(p.id)

        return {
            "total_plans": len(plans),
            "critical_count": len(critical_ids),
            "critical_plan_ids": critical_ids,
            "warning_count": len(warning_ids),
            "warning_plan_ids": warning_ids,
            "healthy_count": len(plans) - len(critical_ids) - len(warning_ids),
        }

    def outliers_summary(self) -> Dict[str, Any]:
        """Statistical outlier detection across the fleet.

        A plan is an outlier if its waste_pct is more than 2 standard
        deviations above the fleet mean.
        """
        plans = self.session.query(CutPlan).all()
        waste_values = [p.waste_pct for p in plans if p.waste_pct is not None]

        if len(waste_values) < 2:
            return {
                "total_plans": len(plans),
                "plans_with_waste_data": len(waste_values),
                "fleet_mean": waste_values[0] if waste_values else None,
                "fleet_std": None,
                "outlier_threshold": None,
                "outlier_count": 0,
                "outlier_plan_ids": [],
            }

        mean = sum(waste_values) / len(waste_values)
        variance = sum((v - mean) ** 2 for v in waste_values) / len(waste_values)
        std = variance ** 0.5
        threshold = mean + 2 * std

        outlier_ids = [
            p.id for p in plans
            if p.waste_pct is not None and p.waste_pct > threshold
        ]

        return {
            "total_plans": len(plans),
            "plans_with_waste_data": len(waste_values),
            "fleet_mean": round(mean, 2),
            "fleet_std": round(std, 2),
            "outlier_threshold": round(threshold, 2),
            "outlier_count": len(outlier_ids),
            "outlier_plan_ids": outlier_ids,
        }

    def plan_alerts(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan alert detail — lists all active alerts for a plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan.id)
        total = len(cuts)
        waste_pct = plan.waste_pct or 0.0

        alerts: list[dict] = []

        if waste_pct > 15.0:
            alerts.append({
                "level": "critical",
                "metric": "waste_pct",
                "value": waste_pct,
                "threshold": 15.0,
                "message": f"Waste {waste_pct:.1f}% critically exceeds 15% limit",
            })
        elif waste_pct > 10.0:
            alerts.append({
                "level": "warning",
                "metric": "waste_pct",
                "value": waste_pct,
                "threshold": 10.0,
                "message": f"Waste {waste_pct:.1f}% exceeds 10% warning level",
            })

        if total > 0:
            scrap_count = sum(1 for c in cuts if c.status == "scrap")
            ok_count = sum(1 for c in cuts if c.status == "ok")
            scrap_rate = scrap_count / total
            yield_pct = (ok_count / total) * 100.0

            if scrap_rate > 0.30:
                alerts.append({
                    "level": "critical",
                    "metric": "scrap_rate",
                    "value": round(scrap_rate * 100, 2),
                    "threshold": 30.0,
                    "message": f"Scrap rate {scrap_rate*100:.1f}% exceeds 30% limit",
                })

            if yield_pct < 50.0:
                alerts.append({
                    "level": "warning",
                    "metric": "yield_pct",
                    "value": round(yield_pct, 2),
                    "threshold": 50.0,
                    "message": f"Yield {yield_pct:.1f}% below 50% minimum",
                })
        else:
            scrap_count = 0
            ok_count = 0
            yield_pct = None

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "total_cuts": total,
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "waste_pct": waste_pct,
            "yield_pct": yield_pct,
            "alert_count": len(alerts),
            "alerts": alerts,
        }

    def export_outliers(self) -> Dict[str, Any]:
        """Export-ready payload combining alerts overview, outliers summary,
        and per-plan alerts."""
        plans = self.session.query(CutPlan).all()
        plan_alerts_list = []
        for p in plans:
            plan_alerts_list.append(self.plan_alerts(p.id))

        return {
            "alerts_overview": self.alerts_overview(),
            "outliers_summary": self.outliers_summary(),
            "plan_alerts": plan_alerts_list,
        }

    # ------------------------------------------------------------------
    # Throughput / Cadence helpers (C43)
    # ------------------------------------------------------------------

    def throughput_overview(self) -> Dict[str, Any]:
        """Fleet-wide throughput summary.

        Computes total cuts across all plans, cuts per plan, yield rate,
        and identifies highest/lowest throughput plans.
        """
        plans = self.session.query(CutPlan).all()

        if not plans:
            return {
                "total_plans": 0,
                "total_cuts": 0,
                "avg_cuts_per_plan": None,
                "max_cuts_plan_id": None,
                "min_cuts_plan_id": None,
                "fleet_yield_pct": None,
            }

        plan_cuts: list[tuple] = []  # (plan_id, cut_count, ok_count)
        total_cuts = 0
        total_ok = 0

        for p in plans:
            cuts = self.list_cuts(p.id)
            n = len(cuts)
            ok = sum(1 for c in cuts if c.status == "ok")
            plan_cuts.append((p.id, n, ok))
            total_cuts += n
            total_ok += ok

        avg_cuts = round(total_cuts / len(plans), 2)
        fleet_yield = round(total_ok / total_cuts * 100, 2) if total_cuts > 0 else None

        max_plan = max(plan_cuts, key=lambda x: x[1])
        min_plan = min(plan_cuts, key=lambda x: x[1])

        return {
            "total_plans": len(plans),
            "total_cuts": total_cuts,
            "avg_cuts_per_plan": avg_cuts,
            "max_cuts_plan_id": max_plan[0],
            "max_cuts_count": max_plan[1],
            "min_cuts_plan_id": min_plan[0],
            "min_cuts_count": min_plan[1],
            "fleet_yield_pct": fleet_yield,
        }

    def cadence_summary(self) -> Dict[str, Any]:
        """Cadence summary: plans grouped by throughput tier.

        - high: >= 5 cuts
        - medium: 2-4 cuts
        - low: 0-1 cuts
        """
        plans = self.session.query(CutPlan).all()

        high_ids: list[str] = []
        medium_ids: list[str] = []
        low_ids: list[str] = []

        for p in plans:
            cuts = self.list_cuts(p.id)
            n = len(cuts)
            if n >= 5:
                high_ids.append(p.id)
            elif n >= 2:
                medium_ids.append(p.id)
            else:
                low_ids.append(p.id)

        return {
            "total_plans": len(plans),
            "high_cadence_count": len(high_ids),
            "high_cadence_plan_ids": high_ids,
            "medium_cadence_count": len(medium_ids),
            "medium_cadence_plan_ids": medium_ids,
            "low_cadence_count": len(low_ids),
            "low_cadence_plan_ids": low_ids,
        }

    def plan_cadence(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan cadence detail: cut count, yield, scrap breakdown,
        and cadence tier classification."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan.id)
        total = len(cuts)
        ok_count = sum(1 for c in cuts if c.status == "ok")
        scrap_count = sum(1 for c in cuts if c.status == "scrap")
        rework_count = sum(1 for c in cuts if c.status == "rework")

        if total >= 5:
            tier = "high"
        elif total >= 2:
            tier = "medium"
        else:
            tier = "low"

        yield_pct = round(ok_count / total * 100, 2) if total > 0 else None

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "total_cuts": total,
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "rework_count": rework_count,
            "yield_pct": yield_pct,
            "cadence_tier": tier,
        }

    def export_cadence(self) -> Dict[str, Any]:
        """Export-ready payload combining throughput overview, cadence
        summary, and per-plan cadence details."""
        plans = self.session.query(CutPlan).all()
        plan_cadences = []
        for p in plans:
            plan_cadences.append(self.plan_cadence(p.id))

        return {
            "throughput_overview": self.throughput_overview(),
            "cadence_summary": self.cadence_summary(),
            "plan_cadences": plan_cadences,
        }

    # ------------------------------------------------------------------
    # Saturation / Bottlenecks helpers (C46)
    # ------------------------------------------------------------------

    def _plan_cut_density(self, plan: CutPlan, cuts: List[CutResult]) -> float:
        material_quantity = plan.material_quantity or 0.0
        if material_quantity > 0:
            return round(len(cuts) / material_quantity, 2)
        return float(len(cuts))

    def _saturation_bucket(self, cut_density: float) -> str:
        if cut_density >= 5.0:
            return "critical"
        if cut_density >= 3.0:
            return "high"
        if cut_density >= 1.0:
            return "medium"
        return "low"

    def saturation_overview(self) -> Dict[str, Any]:
        """Plan-wide saturation summary with density buckets."""
        plans = self.session.query(CutPlan).all()
        bucket_counts = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }

        if not plans:
            return {
                "total_plans": 0,
                "total_cuts": 0,
                "avg_cut_density": None,
                "high_saturation_count": 0,
                "high_saturation_plan_ids": [],
                "bucket_counts": bucket_counts,
            }

        densities: List[float] = []
        total_cuts = 0
        high_saturation_ids: List[str] = []

        for plan in plans:
            cuts = self.list_cuts(plan.id)
            density = self._plan_cut_density(plan, cuts)
            bucket = self._saturation_bucket(density)
            bucket_counts[bucket] += 1
            densities.append(density)
            total_cuts += len(cuts)
            if bucket in {"high", "critical"}:
                high_saturation_ids.append(plan.id)

        return {
            "total_plans": len(plans),
            "total_cuts": total_cuts,
            "avg_cut_density": round(sum(densities) / len(densities), 2),
            "high_saturation_count": len(high_saturation_ids),
            "high_saturation_plan_ids": high_saturation_ids,
            "bucket_counts": bucket_counts,
        }

    def bottlenecks_summary(self) -> Dict[str, Any]:
        """Fleet-level bottleneck summary across materials and plans."""
        plans = self.session.query(CutPlan).all()
        blocker_breakdown = {
            "saturation_high": 0,
            "saturation_critical": 0,
            "low_yield": 0,
            "scrap_heavy": 0,
            "waste_hotspot": 0,
            "material_constrained": 0,
        }

        if not plans:
            return {
                "total_plans": 0,
                "constrained_material_count": 0,
                "constrained_material_ids": [],
                "congested_plan_count": 0,
                "congested_plan_ids": [],
                "blocked_plan_count": 0,
                "blocked_plan_ids": [],
                "blocker_breakdown": blocker_breakdown,
            }

        material_signals: Dict[str, int] = {}
        congested_plan_ids: List[str] = []
        blocked_plan_ids: List[str] = []

        for plan in plans:
            detail = self.plan_bottlenecks(plan.id)
            if detail["saturation_bucket"] in {"high", "critical"}:
                congested_plan_ids.append(plan.id)
            if detail["bottlenecks"]:
                blocked_plan_ids.append(plan.id)
            if detail["material_id"] and (
                detail["saturation_bucket"] in {"high", "critical"}
                or detail["bottlenecks"]
            ):
                material_signals[detail["material_id"]] = (
                    material_signals.get(detail["material_id"], 0) + 1
                )
            for blocker in detail["bottlenecks"]:
                blocker_breakdown[blocker] = blocker_breakdown.get(blocker, 0) + 1

        constrained_material_ids = sorted(
            material_id
            for material_id, signal_count in material_signals.items()
            if signal_count >= 2
        )

        return {
            "total_plans": len(plans),
            "constrained_material_count": len(constrained_material_ids),
            "constrained_material_ids": constrained_material_ids,
            "congested_plan_count": len(congested_plan_ids),
            "congested_plan_ids": congested_plan_ids,
            "blocked_plan_count": len(blocked_plan_ids),
            "blocked_plan_ids": blocked_plan_ids,
            "blocker_breakdown": blocker_breakdown,
        }

    def plan_bottlenecks(self, plan_id: str) -> Dict[str, Any]:
        """Per-plan saturation and bottleneck detail."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        cuts = self.list_cuts(plan.id)
        total_cuts = len(cuts)
        ok_count = sum(1 for cut in cuts if cut.status == CutResultStatus.OK.value)
        scrap_count = sum(
            1 for cut in cuts if cut.status == CutResultStatus.SCRAP.value
        )
        rework_count = sum(
            1 for cut in cuts if cut.status == CutResultStatus.REWORK.value
        )
        cut_density = self._plan_cut_density(plan, cuts)
        saturation_bucket = self._saturation_bucket(cut_density)
        yield_pct = (
            round(ok_count / total_cuts * 100, 2) if total_cuts > 0 else None
        )
        scrap_rate_pct = (
            round(scrap_count / total_cuts * 100, 2) if total_cuts > 0 else None
        )

        bottlenecks: List[str] = []
        if saturation_bucket in {"high", "critical"}:
            bottlenecks.append(f"saturation_{saturation_bucket}")
        if yield_pct is not None and yield_pct < 75.0:
            bottlenecks.append("low_yield")
        if scrap_rate_pct is not None and scrap_rate_pct >= 25.0:
            bottlenecks.append("scrap_heavy")
        if (plan.waste_pct or 0.0) >= 15.0:
            bottlenecks.append("waste_hotspot")
        if cut_density >= 5.0 and (plan.material_quantity or 0.0) <= 1.0:
            bottlenecks.append("material_constrained")

        if "material_constrained" in bottlenecks or saturation_bucket == "critical":
            material_stress = "high"
        elif saturation_bucket in {"medium", "high"}:
            material_stress = "medium"
        else:
            material_stress = "normal"

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "state": plan.state,
            "material_id": plan.material_id,
            "material_quantity": plan.material_quantity,
            "total_cuts": total_cuts,
            "ok_count": ok_count,
            "scrap_count": scrap_count,
            "rework_count": rework_count,
            "waste_pct": plan.waste_pct,
            "yield_pct": yield_pct,
            "scrap_rate_pct": scrap_rate_pct,
            "cut_density": cut_density,
            "saturation_bucket": saturation_bucket,
            "material_stress": material_stress,
            "bottlenecks": bottlenecks,
        }

    def export_bottlenecks(self) -> Dict[str, Any]:
        """Export-ready payload combining saturation and bottleneck detail."""
        plans = self.session.query(CutPlan).all()
        return {
            "saturation_overview": self.saturation_overview(),
            "bottlenecks_summary": self.bottlenecks_summary(),
            "plan_bottlenecks": [self.plan_bottlenecks(plan.id) for plan in plans],
        }
