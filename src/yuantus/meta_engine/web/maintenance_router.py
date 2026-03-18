"""Maintenance management API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.maintenance.service import MaintenanceService

maintenance_router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


# ============================================================================
# Request / Response Models
# ============================================================================


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[str] = None
    description: Optional[str] = None


class EquipmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    serial_number: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    category_id: Optional[str] = None
    location: Optional[str] = None
    plant_code: Optional[str] = None
    workcenter_id: Optional[str] = None
    team_name: Optional[str] = None
    expected_mtbf_days: Optional[float] = None
    properties: Optional[Dict[str, Any]] = None


class EquipmentStatusRequest(BaseModel):
    status: str


class MaintenanceRequestCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    equipment_id: str
    maintenance_type: str = "corrective"
    priority: str = "medium"
    description: Optional[str] = None
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    duration_hours: Optional[float] = None
    team_name: Optional[str] = None


class MaintenanceRequestTransitionRequest(BaseModel):
    target_state: str
    resolution_note: Optional[str] = None


# ============================================================================
# Helpers
# ============================================================================


def _category_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "parent_id": c.parent_id,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _equipment_dict(e) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "serial_number": e.serial_number,
        "model": e.model,
        "manufacturer": e.manufacturer,
        "category_id": e.category_id,
        "status": e.status,
        "location": e.location,
        "plant_code": e.plant_code,
        "workcenter_id": e.workcenter_id,
        "team_name": e.team_name,
        "expected_mtbf_days": e.expected_mtbf_days,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _request_dict(r) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "equipment_id": r.equipment_id,
        "maintenance_type": r.maintenance_type,
        "state": r.state,
        "priority": r.priority,
        "description": r.description,
        "resolution_note": r.resolution_note,
        "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "duration_hours": r.duration_hours,
        "team_name": r.team_name,
        "assigned_user_id": r.assigned_user_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "cancelled_at": r.cancelled_at.isoformat() if r.cancelled_at else None,
    }


# ============================================================================
# Category Endpoints
# ============================================================================


@maintenance_router.post("/categories")
async def create_category(
    req: CategoryCreateRequest,
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    cat = svc.create_category(
        name=req.name, parent_id=req.parent_id, description=req.description
    )
    db.commit()
    return _category_dict(cat)


@maintenance_router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    svc = MaintenanceService(db)
    cats = svc.list_categories()
    return {"total": len(cats), "categories": [_category_dict(c) for c in cats]}


# ============================================================================
# Equipment Endpoints
# ============================================================================


@maintenance_router.post("/equipment")
async def create_equipment(
    req: EquipmentCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    equip = svc.create_equipment(
        name=req.name,
        serial_number=req.serial_number,
        model=req.model,
        manufacturer=req.manufacturer,
        category_id=req.category_id,
        location=req.location,
        plant_code=req.plant_code,
        workcenter_id=req.workcenter_id,
        team_name=req.team_name,
        expected_mtbf_days=req.expected_mtbf_days,
        properties=req.properties,
        user_id=user_id,
    )
    db.commit()
    return _equipment_dict(equip)


@maintenance_router.get("/equipment")
async def list_equipment(
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    plant_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    items = svc.list_equipment(
        status=status, category_id=category_id, plant_code=plant_code
    )
    return {"total": len(items), "equipment": [_equipment_dict(e) for e in items]}


@maintenance_router.get("/equipment/readiness-summary")
async def equipment_readiness_summary(
    plant_code: Optional[str] = Query(None),
    workcenter_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    return svc.get_equipment_readiness_summary(
        plant_code=plant_code,
        workcenter_id=workcenter_id,
    )


@maintenance_router.get("/equipment/{equipment_id}")
async def get_equipment(equipment_id: str, db: Session = Depends(get_db)):
    svc = MaintenanceService(db)
    equip = svc.get_equipment(equipment_id)
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return _equipment_dict(equip)


@maintenance_router.post("/equipment/{equipment_id}/status")
async def update_equipment_status(
    equipment_id: str,
    req: EquipmentStatusRequest,
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    try:
        equip = svc.update_equipment_status(equipment_id, status=req.status)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _equipment_dict(equip)


# ============================================================================
# Maintenance Request Endpoints
# ============================================================================


@maintenance_router.post("/requests")
async def create_maintenance_request(
    req: MaintenanceRequestCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    try:
        mreq = svc.create_request(
            name=req.name,
            equipment_id=req.equipment_id,
            maintenance_type=req.maintenance_type,
            priority=req.priority,
            description=req.description,
            team_name=req.team_name,
            duration_hours=req.duration_hours,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _request_dict(mreq)


@maintenance_router.post("/requests/{request_id}/transition")
async def transition_maintenance_request(
    request_id: str,
    req: MaintenanceRequestTransitionRequest,
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    try:
        mreq = svc.transition_request(
            request_id,
            target_state=req.target_state,
            resolution_note=req.resolution_note,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _request_dict(mreq)


@maintenance_router.get("/requests")
async def list_maintenance_requests(
    equipment_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    maintenance_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    reqs = svc.list_requests(
        equipment_id=equipment_id,
        state=state,
        maintenance_type=maintenance_type,
        priority=priority,
    )
    return {"total": len(reqs), "requests": [_request_dict(r) for r in reqs]}


@maintenance_router.get("/requests/{request_id}")
async def get_maintenance_request(request_id: str, db: Session = Depends(get_db)):
    svc = MaintenanceService(db)
    mreq = svc.get_request(request_id)
    if not mreq:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    return _request_dict(mreq)


# ============================================================================
# C9 – Preventive Schedule & Queue Summary
# ============================================================================


@maintenance_router.get("/preventive-schedule")
async def preventive_schedule(
    window_days: int = Query(30, ge=1, le=365),
    include_overdue: bool = Query(True),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    return svc.get_preventive_schedule(
        window_days=window_days,
        include_overdue=include_overdue,
    )


@maintenance_router.get("/queue-summary")
async def maintenance_queue_summary(
    plant_code: Optional[str] = Query(None),
    workcenter_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    return svc.get_maintenance_queue_summary(
        plant_code=plant_code,
        workcenter_id=workcenter_id,
    )
