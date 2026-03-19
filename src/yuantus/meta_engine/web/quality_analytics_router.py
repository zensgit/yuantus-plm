"""Quality analytics / SPC API endpoints (C16)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.quality.analytics_service import QualityAnalyticsService
from yuantus.meta_engine.quality.service import QualityService
from yuantus.meta_engine.quality.spc_service import QualitySpcService

quality_analytics_router = APIRouter(
    prefix="/quality", tags=["Quality Analytics"]
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class SpcPayload(BaseModel):
    measurements: List[float]
    lsl: float
    usl: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_domain(db: Session):
    """Load checks, alerts, points from the foundation service."""
    svc = QualityService(db)
    checks = svc.list_checks()
    alerts = svc.list_alerts()
    points = svc.list_points()
    return checks, alerts, points


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


@quality_analytics_router.get("/analytics")
async def quality_full_analytics(db: Session = Depends(get_db)):
    checks, alerts, points = _fetch_domain(db)
    svc = QualityAnalyticsService(checks, alerts, points)
    return svc.full_analytics()


@quality_analytics_router.get("/analytics/defect-rates")
async def quality_defect_rates(db: Session = Depends(get_db)):
    checks, alerts, points = _fetch_domain(db)
    svc = QualityAnalyticsService(checks, alerts, points)
    return svc.defect_rate_by_point()


@quality_analytics_router.get("/analytics/alert-aging")
async def quality_alert_aging(db: Session = Depends(get_db)):
    checks, alerts, points = _fetch_domain(db)
    svc = QualityAnalyticsService(checks, alerts, points)
    return svc.alert_aging()


# ---------------------------------------------------------------------------
# SPC endpoints
# ---------------------------------------------------------------------------


@quality_analytics_router.post("/spc")
async def quality_spc_from_payload(payload: SpcPayload):
    svc = QualitySpcService(payload.measurements, payload.lsl, payload.usl)
    cap = svc.capability_indices()
    chart = svc.control_chart_data()
    return {
        "capability": cap,
        "control_chart": chart,
        "out_of_control": svc.out_of_control_indices(),
    }


@quality_analytics_router.get("/spc/{point_id}")
async def quality_spc_from_point(
    point_id: str,
    db: Session = Depends(get_db),
):
    qsvc = QualityService(db)
    point = qsvc.get_point(point_id)
    if not point:
        return {"error": f"Point {point_id} not found"}
    checks = qsvc.list_checks(point_id=point_id)
    spc = QualitySpcService.from_checks(checks, point)
    cap = spc.capability_indices()
    chart = spc.control_chart_data()
    return {
        "point_id": point_id,
        "capability": cap,
        "control_chart": chart,
        "out_of_control": spc.out_of_control_indices(),
    }
