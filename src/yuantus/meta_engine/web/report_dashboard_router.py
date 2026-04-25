from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.reports.report_service import DashboardService

report_dashboard_router = APIRouter(prefix="/reports", tags=["Reports"])


class DashboardCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[Dict[str, Any]]] = None
    auto_refresh: bool = False
    refresh_interval: int = Field(default=300, ge=30, le=3600)
    is_public: bool = False
    is_default: bool = False


class DashboardUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[Dict[str, Any]]] = None
    auto_refresh: Optional[bool] = None
    refresh_interval: Optional[int] = Field(default=None, ge=30, le=3600)
    is_public: Optional[bool] = None
    is_default: Optional[bool] = None


class DashboardResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    layout: Optional[Dict[str, Any]]
    widgets: Optional[List[Dict[str, Any]]]
    auto_refresh: bool
    refresh_interval: int
    owner_id: Optional[int]
    is_public: bool
    is_default: bool
    created_at: Optional[datetime]
    created_by_id: Optional[int]


def _is_admin(user: CurrentUser) -> bool:
    if bool(getattr(user, "is_superuser", False)):
        return True
    roles = {str(role).strip().lower() for role in (user.roles or []) if str(role).strip()}
    return "admin" in roles or "superuser" in roles


def _to_dashboard_response(dashboard) -> DashboardResponse:
    return DashboardResponse(
        id=dashboard.id,
        name=dashboard.name,
        description=dashboard.description,
        layout=dashboard.layout,
        widgets=dashboard.widgets,
        auto_refresh=bool(dashboard.auto_refresh),
        refresh_interval=dashboard.refresh_interval or 300,
        owner_id=dashboard.owner_id,
        is_public=bool(dashboard.is_public),
        is_default=bool(dashboard.is_default),
        created_at=dashboard.created_at,
        created_by_id=dashboard.created_by_id,
    )


@report_dashboard_router.post("/dashboards", response_model=DashboardResponse)
def create_dashboard(
    req: DashboardCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    service = DashboardService(db)
    dashboard = service.create_dashboard(
        name=req.name,
        description=req.description,
        layout=req.layout,
        widgets=req.widgets,
        auto_refresh=req.auto_refresh,
        refresh_interval=req.refresh_interval,
        owner_id=user.id,
        is_public=req.is_public,
        is_default=req.is_default,
        created_by_id=user.id,
    )
    return _to_dashboard_response(dashboard)


@report_dashboard_router.get("/dashboards", response_model=Dict[str, Any])
def list_dashboards(
    include_public: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = DashboardService(db)
    dashboards = service.list_dashboards(owner_id=user.id, include_public=include_public)
    return {"items": [_to_dashboard_response(d).model_dump() for d in dashboards]}


@report_dashboard_router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
def get_dashboard(
    dashboard_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    service = DashboardService(db)
    dashboard = service.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if not _is_admin(user) and not dashboard.is_public and dashboard.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return _to_dashboard_response(dashboard)


@report_dashboard_router.patch("/dashboards/{dashboard_id}", response_model=DashboardResponse)
def update_dashboard(
    dashboard_id: str,
    req: DashboardUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    service = DashboardService(db)
    dashboard = service.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if not _is_admin(user) and dashboard.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    updated = service.update_dashboard(
        dashboard_id,
        name=req.name,
        description=req.description,
        layout=req.layout,
        widgets=req.widgets,
        auto_refresh=req.auto_refresh,
        refresh_interval=req.refresh_interval,
        is_public=req.is_public,
        is_default=req.is_default,
    )
    return _to_dashboard_response(updated)


@report_dashboard_router.delete("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
def delete_dashboard(
    dashboard_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = DashboardService(db)
    dashboard = service.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if not _is_admin(user) and dashboard.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    service.delete_dashboard(dashboard_id)
    return {"status": "deleted", "id": dashboard_id}
