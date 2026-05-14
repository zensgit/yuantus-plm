"""Subcontracting approval role mapping API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.subcontracting.service import SubcontractingService

subcontracting_approval_mapping_router = APIRouter(
    prefix="/subcontracting", tags=["Subcontracting"]
)


class ApprovalRoleMappingRequest(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=100)
    scope_type: str = Field(..., min_length=1, max_length=30)
    scope_value: Optional[str] = None
    scope_vendor_id: Optional[str] = None
    scope_policy_code: Optional[str] = None
    owner: Optional[str] = None
    team: Optional[str] = None
    required: bool = False
    sequence: int = Field(10, gt=0)
    fallback_role: Optional[str] = None
    active: bool = True
    properties: Optional[Dict[str, Any]] = None


def _normalize_export_format(fmt: str) -> str:
    normalized = str(fmt or "json").strip().lower()
    if normalized not in {"json", "csv", "markdown"}:
        raise HTTPException(status_code=400, detail="format must be one of: json, csv, markdown")
    return normalized


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


@subcontracting_approval_mapping_router.post("/approval-role-mappings")
async def upsert_subcontracting_approval_role_mapping(
    req: ApprovalRoleMappingRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        svc.upsert_approval_role_mapping(
            role_code=req.role_code,
            scope_type=req.scope_type,
            scope_value=req.scope_value,
            scope_vendor_id=req.scope_vendor_id,
            scope_policy_code=req.scope_policy_code,
            owner=req.owner,
            team=req.team,
            required=req.required,
            sequence=req.sequence,
            fallback_role=req.fallback_role,
            active=req.active,
            properties=req.properties,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = svc.get_approval_role_mapping_registry()
    payload["urls"] = {
        "self": "/api/v1/subcontracting/approval-role-mappings",
        "export": "/api/v1/subcontracting/approval-role-mappings/export?format=json",
    }
    return payload


@subcontracting_approval_mapping_router.get("/approval-role-mappings")
async def subcontracting_approval_role_mapping_registry(
    scope_type: Optional[str] = Query(None),
    scope_value: Optional[str] = Query(None),
    scope_vendor_id: Optional[str] = Query(None),
    scope_policy_code: Optional[str] = Query(None),
    role_code: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(200, ge=1, le=500),
    sort_by: str = Query("scope"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.get_approval_role_mapping_registry(
            scope_type=scope_type,
            scope_value=scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
            role_code=role_code,
            active_only=active_only,
            limit=limit,
            sort_by=sort_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload["urls"] = {
        "self": "/api/v1/subcontracting/approval-role-mappings",
        "export": "/api/v1/subcontracting/approval-role-mappings/export?format=json",
    }
    return payload


@subcontracting_approval_mapping_router.get("/approval-role-mappings/export")
async def export_subcontracting_approval_role_mapping_registry(
    format: str = Query("json"),
    scope_type: Optional[str] = Query(None),
    scope_value: Optional[str] = Query(None),
    scope_vendor_id: Optional[str] = Query(None),
    scope_policy_code: Optional[str] = Query(None),
    role_code: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(200, ge=1, le=500),
    sort_by: str = Query("scope"),
    db: Session = Depends(get_db),
):
    normalized_format = _normalize_export_format(format)
    svc = SubcontractingService(db)
    try:
        payload = svc.export_approval_role_mapping_registry(
            fmt=normalized_format,
            scope_type=scope_type,
            scope_value=scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
            role_code=role_code,
            active_only=active_only,
            limit=limit,
            sort_by=sort_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _export_response(
        payload=payload,
        fmt=normalized_format,
        stem="subcontracting-approval-role-mappings",
    )
