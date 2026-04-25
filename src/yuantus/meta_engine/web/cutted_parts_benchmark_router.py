"""Cutted-parts benchmark and quote endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_benchmark_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_benchmark_router.get("/benchmark/overview")
def benchmark_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.benchmark_overview()


@cutted_parts_benchmark_router.get("/plans/{plan_id}/quote-summary")
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


@cutted_parts_benchmark_router.get("/materials/benchmarks")
def material_benchmarks(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_benchmarks()


@cutted_parts_benchmark_router.get("/export/quotes")
def export_quotes(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_quotes()
