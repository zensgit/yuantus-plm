"""Maintenance request API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.maintenance.service import MaintenanceService

maintenance_request_router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


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


@maintenance_request_router.post("/requests")
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


@maintenance_request_router.post("/requests/{request_id}/transition")
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


@maintenance_request_router.get("/requests")
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


@maintenance_request_router.get("/requests/{request_id}")
async def get_maintenance_request(request_id: str, db: Session = Depends(get_db)):
    svc = MaintenanceService(db)
    mreq = svc.get_request(request_id)
    if not mreq:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    return _request_dict(mreq)
