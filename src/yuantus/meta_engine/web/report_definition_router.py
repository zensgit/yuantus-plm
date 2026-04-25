from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.reports.report_service import ReportDefinitionService

report_definition_router = APIRouter(prefix="/reports", tags=["Reports"])


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


class ReportExecutionResponse(BaseModel):
    id: str
    report_id: str
    status: str
    error_message: Optional[str]
    row_count: Optional[int]
    execution_time_ms: Optional[int]
    export_format: Optional[str]
    export_path: Optional[str]
    executed_at: Optional[datetime]
    executed_by_id: Optional[int]
    completed_at: Optional[datetime]


def _is_admin(user: CurrentUser) -> bool:
    if bool(getattr(user, "is_superuser", False)):
        return True
    roles = {str(role).strip().lower() for role in (user.roles or []) if str(role).strip()}
    return "admin" in roles or "superuser" in roles


def _can_access_report(report, user: CurrentUser) -> bool:
    if _is_admin(user):
        return True
    if report.owner_id == user.id:
        return True
    if report.is_public:
        allowed = report.allowed_roles or []
        if not allowed:
            return True
        allowed_roles = {str(role).strip().lower() for role in allowed if str(role).strip()}
        user_roles = {
            str(role).strip().lower() for role in (user.roles or []) if str(role).strip()
        }
        return bool(allowed_roles & user_roles)
    return False


def _to_report_definition_response(report) -> ReportDefinitionResponse:
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


def _to_report_execution_response(execution) -> ReportExecutionResponse:
    return ReportExecutionResponse(
        id=execution.id,
        report_id=execution.report_id,
        status=execution.status,
        error_message=execution.error_message,
        row_count=execution.row_count,
        execution_time_ms=execution.execution_time_ms,
        export_format=execution.export_format,
        export_path=execution.export_path,
        executed_at=execution.executed_at,
        executed_by_id=execution.executed_by_id,
        completed_at=execution.completed_at,
    )


@report_definition_router.post("/definitions", response_model=ReportDefinitionResponse)
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
    return _to_report_definition_response(report)


@report_definition_router.get("/definitions", response_model=Dict[str, Any])
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
    if not _is_admin(user):
        reports = [report for report in reports if _can_access_report(report, user)]
    return {"items": [_to_report_definition_response(report).model_dump() for report in reports]}


@report_definition_router.get("/definitions/{report_id}", response_model=ReportDefinitionResponse)
def get_report_definition(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDefinitionResponse:
    service = ReportDefinitionService(db)
    report = service.get_definition(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _can_access_report(report, user):
        raise HTTPException(status_code=403, detail="Permission denied")
    return _to_report_definition_response(report)


@report_definition_router.patch("/definitions/{report_id}", response_model=ReportDefinitionResponse)
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
    return _to_report_definition_response(updated)


@report_definition_router.delete("/definitions/{report_id}", response_model=Dict[str, Any])
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


@report_definition_router.post("/definitions/{report_id}/execute", response_model=Dict[str, Any])
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
    if not _can_access_report(report, user):
        raise HTTPException(status_code=403, detail="Permission denied")
    return service.execute_definition(
        report_id,
        parameters=req.parameters,
        user_id=user.id,
        page=req.page,
        page_size=req.page_size,
    )


@report_definition_router.post("/definitions/{report_id}/export")
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
    if not _can_access_report(report, user):
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
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers=headers,
    )


@report_definition_router.get("/executions", response_model=Dict[str, Any])
def list_report_executions(
    report_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = ReportDefinitionService(db)
    executed_by_id: Optional[int] = None
    if report_id:
        report = service.get_definition(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report definition not found")
        if not _can_access_report(report, user):
            raise HTTPException(status_code=403, detail="Permission denied")
        if not _is_admin(user) and report.owner_id != user.id:
            executed_by_id = user.id
    elif not _is_admin(user):
        executed_by_id = user.id

    executions = service.list_executions(
        report_id=report_id,
        executed_by_id=executed_by_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [_to_report_execution_response(ex).model_dump() for ex in executions],
        "count": len(executions),
    }


@report_definition_router.get("/executions/{execution_id}", response_model=ReportExecutionResponse)
def get_report_execution(
    execution_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportExecutionResponse:
    service = ReportDefinitionService(db)
    execution = service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Report execution not found")

    report = service.get_definition(execution.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report definition not found")
    if not _can_access_report(report, user):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not _is_admin(user) and report.owner_id != user.id and execution.executed_by_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    return _to_report_execution_response(execution)
