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
        return (
            self.session.query(CutResult)
            .filter(CutResult.plan_id == plan_id)
            .order_by(CutResult.created_at)
            .all()
        )

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
