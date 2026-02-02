from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user, get_current_user_optional
from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.reports.report_service import DashboardService, ReportDefinitionService
from yuantus.meta_engine.reports.search_service import AdvancedSearchService, SavedSearchService
from yuantus.meta_engine.services.report_service import ReportService

report_router = APIRouter(prefix="/reports", tags=["Reports"])


class AdvancedSearchRequest(BaseModel):
    item_type_id: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    full_text: Optional[str] = None
    sort: Optional[List[Dict[str, str]]] = None
    columns: Optional[List[str]] = None
    page: int = 1
    page_size: int = 25
    include_count: bool = True


class SavedSearchCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_public: bool = False
    item_type_id: Optional[str] = None
    criteria: Dict[str, Any] = Field(default_factory=dict)
    display_columns: Optional[List[str]] = None
    page_size: int = Field(default=25, ge=1, le=1000)


class SavedSearchUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_public: Optional[bool] = None
    item_type_id: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    display_columns: Optional[List[str]] = None
    page_size: Optional[int] = Field(default=None, ge=1, le=1000)


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: Optional[int]
    is_public: bool
    item_type_id: Optional[str]
    criteria: Dict[str, Any]
    display_columns: Optional[List[str]]
    page_size: int
    use_count: int
    last_used_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ReportDefinitionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=100)
    report_type: str = Field(default="table", max_length=50)
    data_source: Dict[str, Any]
    layout: Optional[Dict[str, Any]] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    is_public: bool = False
    allowed_roles: Optional[List[str]] = None
    is_active: bool = True


class ReportDefinitionUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    code: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=100)
    report_type: Optional[str] = Field(default=None, max_length=50)
    data_source: Optional[Dict[str, Any]] = None
    layout: Optional[Dict[str, Any]] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = None
    allowed_roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ReportDefinitionResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    description: Optional[str]
    category: Optional[str]
    report_type: str
    data_source: Dict[str, Any]
    layout: Optional[Dict[str, Any]]
    parameters: Optional[List[Dict[str, Any]]]
    owner_id: Optional[int]
    is_public: bool
    allowed_roles: Optional[List[str]]
    is_active: bool
    created_at: Optional[datetime]
    created_by_id: Optional[int]
    updated_at: Optional[datetime]


class ReportExecuteRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = None
    page: int = 1
    page_size: int = 200


class ReportExportRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = None
    page: int = 1
    page_size: int = 1000
    export_format: str = Field(default="csv", max_length=20)


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
    roles = set(user.roles or [])
    return "admin" in roles or "superuser" in roles


@report_router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
):
    service = ReportService(db)
    ctx = get_request_context()
    settings = get_settings()
    summary = service.get_summary()
    summary["meta"] = {
        "tenant_id": ctx.tenant_id,
        "org_id": ctx.org_id,
        "tenancy_mode": settings.TENANCY_MODE,
        "generated_at": datetime.utcnow().isoformat(),
    }
    return summary


@report_router.post("/search", response_model=Dict[str, Any])
def advanced_search(
    req: AdvancedSearchRequest,
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = AdvancedSearchService(db)
    return service.search(
        item_type_id=req.item_type_id,
        filters=req.filters,
        full_text=req.full_text,
        sort=req.sort,
        columns=req.columns,
        page=req.page,
        page_size=req.page_size,
        include_count=req.include_count,
    )


@report_router.post("/saved-searches", response_model=SavedSearchResponse)
def create_saved_search(
    req: SavedSearchCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearchResponse:
    service = SavedSearchService(db)
    saved = service.create_saved_search(
        name=req.name,
        description=req.description,
        owner_id=user.id,
        is_public=req.is_public,
        item_type_id=req.item_type_id,
        criteria=req.criteria,
        display_columns=req.display_columns,
        page_size=req.page_size,
    )
    return SavedSearchResponse(
        id=saved.id,
        name=saved.name,
        description=saved.description,
        owner_id=saved.owner_id,
        is_public=bool(saved.is_public),
        item_type_id=saved.item_type_id,
        criteria=saved.criteria or {},
        display_columns=saved.display_columns,
        page_size=saved.page_size or 25,
        use_count=saved.use_count or 0,
        last_used_at=saved.last_used_at,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )


@report_router.get("/saved-searches", response_model=Dict[str, Any])
def list_saved_searches(
    include_public: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SavedSearchService(db)
    items = service.list_saved_searches(owner_id=user.id, include_public=include_public)
    return {
        "items": [
            SavedSearchResponse(
                id=ss.id,
                name=ss.name,
                description=ss.description,
                owner_id=ss.owner_id,
                is_public=bool(ss.is_public),
                item_type_id=ss.item_type_id,
                criteria=ss.criteria or {},
                display_columns=ss.display_columns,
                page_size=ss.page_size or 25,
                use_count=ss.use_count or 0,
                last_used_at=ss.last_used_at,
                created_at=ss.created_at,
                updated_at=ss.updated_at,
            ).model_dump()
            for ss in items
        ]
    }


@report_router.get("/saved-searches/{saved_search_id}", response_model=SavedSearchResponse)
def get_saved_search(
    saved_search_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearchResponse:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and not saved.is_public and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return SavedSearchResponse(
        id=saved.id,
        name=saved.name,
        description=saved.description,
        owner_id=saved.owner_id,
        is_public=bool(saved.is_public),
        item_type_id=saved.item_type_id,
        criteria=saved.criteria or {},
        display_columns=saved.display_columns,
        page_size=saved.page_size or 25,
        use_count=saved.use_count or 0,
        last_used_at=saved.last_used_at,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )


@report_router.patch("/saved-searches/{saved_search_id}", response_model=SavedSearchResponse)
def update_saved_search(
    saved_search_id: str,
    req: SavedSearchUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearchResponse:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    updated = service.update_saved_search(
        saved_search_id,
        name=req.name,
        description=req.description,
        is_public=req.is_public,
        item_type_id=req.item_type_id,
        criteria=req.criteria,
        display_columns=req.display_columns,
        page_size=req.page_size,
    )
    return SavedSearchResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        owner_id=updated.owner_id,
        is_public=bool(updated.is_public),
        item_type_id=updated.item_type_id,
        criteria=updated.criteria or {},
        display_columns=updated.display_columns,
        page_size=updated.page_size or 25,
        use_count=updated.use_count or 0,
        last_used_at=updated.last_used_at,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@report_router.delete("/saved-searches/{saved_search_id}", response_model=Dict[str, Any])
def delete_saved_search(
    saved_search_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    service.delete_saved_search(saved_search_id)
    return {"status": "deleted", "id": saved_search_id}


@report_router.post("/saved-searches/{saved_search_id}/run", response_model=Dict[str, Any])
def run_saved_search(
    saved_search_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and not saved.is_public and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    return service.run_saved_search(
        saved_search_id,
        page=page,
        page_size=page_size or None,
    )


@report_router.post("/definitions", response_model=ReportDefinitionResponse)
def create_report_definition(
    req: ReportDefinitionCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDefinitionResponse:
    service = ReportDefinitionService(db)
    report = service.create_definition(
        name=req.name,
        code=req.code,
        description=req.description,
        category=req.category,
        report_type=req.report_type,
        data_source=req.data_source,
        layout=req.layout,
        parameters=req.parameters,
        owner_id=user.id,
        is_public=req.is_public,
        allowed_roles=req.allowed_roles,
        is_active=req.is_active,
        created_by_id=user.id,
    )
    return ReportDefinitionResponse(
        id=report.id,
        name=report.name,
        code=report.code,
        description=report.description,
        category=report.category,
        report_type=report.report_type,
        data_source=report.data_source or {},
        layout=report.layout,
        parameters=report.parameters,
        owner_id=report.owner_id,
        is_public=bool(report.is_public),
        allowed_roles=report.allowed_roles,
        is_active=bool(report.is_active),
        created_at=report.created_at,
        created_by_id=report.created_by_id,
        updated_at=report.updated_at,
    )


@report_router.get("/definitions", response_model=Dict[str, Any])
def list_report_definitions(
    include_public: bool = Query(True),
    active_only: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = ReportDefinitionService(db)
    reports = service.list_definitions(
        owner_id=user.id,
        include_public=include_public,
        active_only=active_only,
    )
    return {
        "items": [
            ReportDefinitionResponse(
                id=r.id,
                name=r.name,
                code=r.code,
                description=r.description,
                category=r.category,
                report_type=r.report_type,
                data_source=r.data_source or {},
                layout=r.layout,
                parameters=r.parameters,
                owner_id=r.owner_id,
                is_public=bool(r.is_public),
                allowed_roles=r.allowed_roles,
                is_active=bool(r.is_active),
                created_at=r.created_at,
                created_by_id=r.created_by_id,
                updated_at=r.updated_at,
            ).model_dump()
            for r in reports
        ]
    }


@report_router.get("/definitions/{report_id}", response_model=ReportDefinitionResponse)
def get_report_definition(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDefinitionResponse:
    service = ReportDefinitionService(db)
    report = service.get_definition(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _is_admin(user) and not report.is_public and report.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return ReportDefinitionResponse(
        id=report.id,
        name=report.name,
        code=report.code,
        description=report.description,
        category=report.category,
        report_type=report.report_type,
        data_source=report.data_source or {},
        layout=report.layout,
        parameters=report.parameters,
        owner_id=report.owner_id,
        is_public=bool(report.is_public),
        allowed_roles=report.allowed_roles,
        is_active=bool(report.is_active),
        created_at=report.created_at,
        created_by_id=report.created_by_id,
        updated_at=report.updated_at,
    )


@report_router.patch("/definitions/{report_id}", response_model=ReportDefinitionResponse)
def update_report_definition(
    report_id: str,
    req: ReportDefinitionUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDefinitionResponse:
    service = ReportDefinitionService(db)
    report = service.get_definition(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _is_admin(user) and report.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    updated = service.update_definition(
        report_id,
        name=req.name,
        code=req.code,
        description=req.description,
        category=req.category,
        report_type=req.report_type,
        data_source=req.data_source,
        layout=req.layout,
        parameters=req.parameters,
        is_public=req.is_public,
        allowed_roles=req.allowed_roles,
        is_active=req.is_active,
    )
    return ReportDefinitionResponse(
        id=updated.id,
        name=updated.name,
        code=updated.code,
        description=updated.description,
        category=updated.category,
        report_type=updated.report_type,
        data_source=updated.data_source or {},
        layout=updated.layout,
        parameters=updated.parameters,
        owner_id=updated.owner_id,
        is_public=bool(updated.is_public),
        allowed_roles=updated.allowed_roles,
        is_active=bool(updated.is_active),
        created_at=updated.created_at,
        created_by_id=updated.created_by_id,
        updated_at=updated.updated_at,
    )


@report_router.delete("/definitions/{report_id}", response_model=Dict[str, Any])
def delete_report_definition(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = ReportDefinitionService(db)
    report = service.get_definition(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _is_admin(user) and report.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    service.delete_definition(report_id)
    return {"status": "deleted", "id": report_id}


@report_router.post("/definitions/{report_id}/execute", response_model=Dict[str, Any])
def execute_report_definition(
    report_id: str,
    req: ReportExecuteRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = ReportDefinitionService(db)
    report = service.get_definition(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _is_admin(user) and not report.is_public and report.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return service.execute_definition(
        report_id,
        parameters=req.parameters,
        user_id=user.id,
        page=req.page,
        page_size=req.page_size,
    )


@report_router.post("/definitions/{report_id}/export")
def export_report_definition(
    report_id: str,
    req: ReportExportRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service = ReportDefinitionService(db)
    report = service.get_definition(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _is_admin(user) and not report.is_public and report.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        result = service.export_definition(
            report_id,
            export_format=req.export_format,
            parameters=req.parameters,
            user_id=user.id,
            page=req.page,
            page_size=req.page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"report_{report_id}.{result['extension']}"
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers=headers,
    )


@report_router.post("/dashboards", response_model=DashboardResponse)
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


@report_router.get("/dashboards", response_model=Dict[str, Any])
def list_dashboards(
    include_public: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = DashboardService(db)
    dashboards = service.list_dashboards(owner_id=user.id, include_public=include_public)
    return {
        "items": [
            DashboardResponse(
                id=d.id,
                name=d.name,
                description=d.description,
                layout=d.layout,
                widgets=d.widgets,
                auto_refresh=bool(d.auto_refresh),
                refresh_interval=d.refresh_interval or 300,
                owner_id=d.owner_id,
                is_public=bool(d.is_public),
                is_default=bool(d.is_default),
                created_at=d.created_at,
                created_by_id=d.created_by_id,
            ).model_dump()
            for d in dashboards
        ]
    }


@report_router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
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


@report_router.patch("/dashboards/{dashboard_id}", response_model=DashboardResponse)
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
    return DashboardResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        layout=updated.layout,
        widgets=updated.widgets,
        auto_refresh=bool(updated.auto_refresh),
        refresh_interval=updated.refresh_interval or 300,
        owner_id=updated.owner_id,
        is_public=bool(updated.is_public),
        is_default=bool(updated.is_default),
        created_at=updated.created_at,
        created_by_id=updated.created_by_id,
    )


@report_router.delete("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
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
