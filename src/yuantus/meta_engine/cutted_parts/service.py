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
