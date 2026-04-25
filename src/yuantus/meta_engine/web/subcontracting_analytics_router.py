"""Subcontracting analytics / export API endpoints."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.subcontracting.service import SubcontractingService

subcontracting_analytics_router = APIRouter(prefix="/subcontracting", tags=["Subcontracting"])


def _export_response(
    *,
    payload: Dict[str, Any] | str,
    fmt: str,
    stem: str,
):
    if fmt == "json":
        return JSONResponse(
            content=payload,
            headers={"content-disposition": f'attachment; filename="{stem}.json"'},
        )
    if fmt == "csv":
        return PlainTextResponse(
            content=str(payload),
            media_type="text/csv; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{stem}.csv"'},
        )
    if fmt == "markdown":
        return PlainTextResponse(
            content=str(payload),
            media_type="text/markdown; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{stem}.md"'},
        )
    raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


@subcontracting_analytics_router.get("/overview")
async def subcontracting_overview(db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    return svc.get_overview()


@subcontracting_analytics_router.get("/vendors/analytics")
async def subcontracting_vendor_analytics(db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    return svc.get_vendor_analytics()


@subcontracting_analytics_router.get("/receipts/analytics")
async def subcontracting_receipt_analytics(db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    return svc.get_receipt_analytics()


@subcontracting_analytics_router.get("/export/overview")
async def export_subcontracting_overview(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.export_overview(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(payload=payload, fmt=format, stem="subcontracting-overview")


@subcontracting_analytics_router.get("/export/vendors")
async def export_subcontracting_vendors(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.export_vendor_analytics(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(payload=payload, fmt=format, stem="subcontracting-vendors")


@subcontracting_analytics_router.get("/export/receipts")
async def export_subcontracting_receipts(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.export_receipt_analytics(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(payload=payload, fmt=format, stem="subcontracting-receipts")
