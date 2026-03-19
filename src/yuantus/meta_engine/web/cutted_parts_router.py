"""
Cutted-parts / cutting-plan router.

Provides plan lifecycle, cut results, material listing, and summary endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.models import CutPlan, CutResult, RawMaterial
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService

cutted_parts_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class PlanCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    material_id: Optional[str] = None
    material_quantity: float = 1.0
    properties: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _plan_dict(plan: CutPlan) -> Dict[str, Any]:
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "state": plan.state,
        "material_id": plan.material_id,
        "material_quantity": plan.material_quantity,
        "total_parts": plan.total_parts,
        "ok_count": plan.ok_count,
        "scrap_count": plan.scrap_count,
        "rework_count": plan.rework_count,
        "waste_pct": plan.waste_pct,
    }


def _cut_dict(cut: CutResult) -> Dict[str, Any]:
    return {
        "id": cut.id,
        "plan_id": cut.plan_id,
        "part_id": cut.part_id,
        "length": cut.length,
        "width": cut.width,
        "quantity": cut.quantity,
        "status": cut.status,
        "scrap_weight": cut.scrap_weight,
        "note": cut.note,
    }


def _material_dict(mat: RawMaterial) -> Dict[str, Any]:
    return {
        "id": mat.id,
        "name": mat.name,
        "material_type": mat.material_type,
        "grade": mat.grade,
        "length": mat.length,
        "width": mat.width,
        "thickness": mat.thickness,
        "dimension_unit": mat.dimension_unit,
        "weight_per_unit": mat.weight_per_unit,
        "weight_unit": mat.weight_unit,
        "stock_quantity": mat.stock_quantity,
        "cost_per_unit": mat.cost_per_unit,
        "is_active": mat.is_active,
    }


# ---------------------------------------------------------------------------
# Plan endpoints
# ---------------------------------------------------------------------------


@cutted_parts_router.post("/plans")
def create_plan(
    request: PlanCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        plan = service.create_plan(
            name=request.name,
            description=request.description,
            material_id=request.material_id,
            material_quantity=request.material_quantity,
            properties=request.properties,
            created_by_id=user.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, **_plan_dict(plan)}


@cutted_parts_router.get("/plans")
def list_plans(
    state: Optional[str] = Query(None),
    material_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    plans = service.list_plans(state=state, material_id=material_id)
    return {"plans": [_plan_dict(p) for p in plans], "count": len(plans)}


@cutted_parts_router.get("/plans/{plan_id}")
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found")
    return _plan_dict(plan)


@cutted_parts_router.get("/plans/{plan_id}/summary")
def get_plan_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        summary = service.plan_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return summary


@cutted_parts_router.get("/plans/{plan_id}/cuts")
def list_cuts(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found")
    cuts = service.list_cuts(plan_id)
    return {"cuts": [_cut_dict(c) for c in cuts], "count": len(cuts)}


# ---------------------------------------------------------------------------
# Material endpoint
# ---------------------------------------------------------------------------


@cutted_parts_router.get("/materials")
def list_materials(
    material_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    materials = service.list_materials(
        material_type=material_type, is_active=is_active
    )
    return {
        "materials": [_material_dict(m) for m in materials],
        "count": len(materials),
    }


# ---------------------------------------------------------------------------
# Analytics / export endpoints (C22)
# ---------------------------------------------------------------------------


@cutted_parts_router.get("/overview")
def cutted_parts_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.overview()


@cutted_parts_router.get("/materials/analytics")
def material_analytics(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_analytics()


@cutted_parts_router.get("/plans/{plan_id}/waste-summary")
def waste_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.waste_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@cutted_parts_router.get("/export/overview")
def export_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_overview()


@cutted_parts_router.get("/export/waste")
def export_waste(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_waste()


# ---------------------------------------------------------------------------
# Cost / Utilization endpoints (C25)
# ---------------------------------------------------------------------------


@cutted_parts_router.get("/utilization/overview")
def utilization_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.utilization_overview()


@cutted_parts_router.get("/materials/utilization")
def material_utilization(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_utilization()


@cutted_parts_router.get("/plans/{plan_id}/cost-summary")
def plan_cost_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_cost_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@cutted_parts_router.get("/export/utilization")
def export_utilization(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_utilization()


@cutted_parts_router.get("/export/costs")
def export_costs(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_costs()


# ---------------------------------------------------------------------------
# Templates / Scenarios endpoints (C28)
# ---------------------------------------------------------------------------


@cutted_parts_router.get("/templates/overview")
def template_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.template_overview()


@cutted_parts_router.get("/plans/{plan_id}/scenarios")
def scenario_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.scenario_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@cutted_parts_router.get("/materials/templates")
def material_templates(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_templates()


@cutted_parts_router.get("/export/scenarios")
def export_scenarios(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_scenarios()


# ---------------------------------------------------------------------------
# Benchmark / Quote endpoints (C31)
# ---------------------------------------------------------------------------


@cutted_parts_router.get("/benchmark/overview")
def benchmark_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.benchmark_overview()


@cutted_parts_router.get("/plans/{plan_id}/quote-summary")
def quote_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.quote_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@cutted_parts_router.get("/materials/benchmarks")
def material_benchmarks(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_benchmarks()


@cutted_parts_router.get("/export/quotes")
def export_quotes(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_quotes()
