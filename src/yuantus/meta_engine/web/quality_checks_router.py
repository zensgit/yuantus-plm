"""Quality check API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.quality.service import QualityService
from yuantus.meta_engine.web.quality_common import (
    QualityCheckCreateRequest,
    QualityCheckRecordRequest,
    check_to_dict,
)

quality_checks_router = APIRouter(prefix="/quality", tags=["Quality"])


@quality_checks_router.post("/checks")
async def create_quality_check(
    req: QualityCheckCreateRequest,
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        check = svc.create_check(
            point_id=req.point_id,
            product_id=req.product_id,
            source_document_ref=req.source_document_ref,
            lot_serial=req.lot_serial,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return check_to_dict(check)


@quality_checks_router.post("/checks/{check_id}/record")
async def record_quality_check(
    check_id: str,
    req: QualityCheckRecordRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        check = svc.record_check_result(
            check_id,
            result=req.result,
            measure_value=req.measure_value,
            picture_path=req.picture_path,
            worksheet_data=req.worksheet_data,
            note=req.note,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return check_to_dict(check)


@quality_checks_router.get("/checks")
async def list_quality_checks(
    point_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    routing_id: Optional[str] = Query(None),
    operation_id: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    checks = svc.list_checks(
        point_id=point_id,
        product_id=product_id,
        routing_id=routing_id,
        operation_id=operation_id,
        result=result,
    )
    return {"total": len(checks), "checks": [check_to_dict(check) for check in checks]}


@quality_checks_router.get("/checks/{check_id}")
async def get_quality_check(check_id: str, db: Session = Depends(get_db)):
    svc = QualityService(db)
    check = svc.get_check(check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")
    return check_to_dict(check)
