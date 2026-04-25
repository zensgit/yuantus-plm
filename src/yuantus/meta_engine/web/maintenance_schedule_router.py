"""Maintenance schedule and queue summary API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.maintenance.service import MaintenanceService

maintenance_schedule_router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


@maintenance_schedule_router.get("/preventive-schedule")
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


@maintenance_schedule_router.get("/queue-summary")
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
