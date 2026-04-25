"""Maintenance equipment API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.maintenance.service import MaintenanceService

maintenance_equipment_router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


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


@maintenance_equipment_router.post("/equipment")
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


@maintenance_equipment_router.get("/equipment")
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


@maintenance_equipment_router.get("/equipment/readiness-summary")
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


@maintenance_equipment_router.get("/equipment/{equipment_id}")
async def get_equipment(equipment_id: str, db: Session = Depends(get_db)):
    svc = MaintenanceService(db)
    equip = svc.get_equipment(equipment_id)
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return _equipment_dict(equip)


@maintenance_equipment_router.post("/equipment/{equipment_id}/status")
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
