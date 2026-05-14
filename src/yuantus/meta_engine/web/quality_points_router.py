"""Quality point API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.quality.service import QualityService
from yuantus.meta_engine.web.quality_common import (
    QualityPointCreateRequest,
    QualityPointUpdateRequest,
    point_to_dict,
)

quality_points_router = APIRouter(prefix="/quality", tags=["Quality"])


@quality_points_router.post("/points")
async def create_quality_point(
    req: QualityPointCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        point = svc.create_point(
            name=req.name,
            check_type=req.check_type,
            product_id=req.product_id,
            item_type_id=req.item_type_id,
            routing_id=req.routing_id,
            operation_id=req.operation_id,
            trigger_on=req.trigger_on,
            measure_min=req.measure_min,
            measure_max=req.measure_max,
            measure_unit=req.measure_unit,
            measure_tolerance=req.measure_tolerance,
            worksheet_template=req.worksheet_template,
            instructions=req.instructions,
            team_name=req.team_name,
            sequence=req.sequence,
            properties=req.properties,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return point_to_dict(point)


@quality_points_router.get("/points")
async def list_quality_points(
    product_id: Optional[str] = Query(None),
    item_type_id: Optional[str] = Query(None),
    routing_id: Optional[str] = Query(None),
    operation_id: Optional[str] = Query(None),
    check_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    points = svc.list_points(
        product_id=product_id,
        item_type_id=item_type_id,
        routing_id=routing_id,
        operation_id=operation_id,
        check_type=check_type,
        is_active=is_active,
    )
    return {"total": len(points), "points": [point_to_dict(point) for point in points]}


@quality_points_router.get("/points/{point_id}")
async def get_quality_point(point_id: str, db: Session = Depends(get_db)):
    svc = QualityService(db)
    point = svc.get_point(point_id)
    if not point:
        raise HTTPException(status_code=404, detail="Quality point not found")
    return point_to_dict(point)


@quality_points_router.patch("/points/{point_id}")
async def update_quality_point(
    point_id: str,
    req: QualityPointUpdateRequest,
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    fields = {key: value for key, value in req.model_dump(exclude_unset=True).items()}
    point = svc.update_point(point_id, **fields)
    if not point:
        raise HTTPException(status_code=404, detail="Quality point not found")
    db.commit()
    return point_to_dict(point)
