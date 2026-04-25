"""Generic approval request API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.approvals.service import ApprovalService

approval_request_router = APIRouter(prefix="/approvals", tags=["Approvals"])

C12_DEFAULT_HISTORY_LIMIT = 5
C12_MAX_BATCH_REQUEST_IDS = 200


class ApprovalRequestCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    category_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    priority: str = "normal"
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None


class ApprovalTransitionRequest(BaseModel):
    target_state: str
    rejection_reason: Optional[str] = None


class ApprovalBatchRequest(BaseModel):
    request_ids: List[str]


def _request_dict(r) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "category_id": r.category_id,
        "entity_type": r.entity_type,
        "entity_id": r.entity_id,
        "state": r.state,
        "priority": r.priority,
        "description": r.description,
        "rejection_reason": r.rejection_reason,
        "requested_by_id": r.requested_by_id,
        "assigned_to_id": r.assigned_to_id,
        "decided_by_id": r.decided_by_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "cancelled_at": r.cancelled_at.isoformat() if r.cancelled_at else None,
        "age_hours": ApprovalService._age_hours(r.created_at),
        "properties": getattr(r, "properties", None) or {},
    }


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


def _normalize_batch_request_ids(request_ids: List[str]) -> List[str]:
    normalized: List[str] = []
    for request_id in request_ids:
        if not isinstance(request_id, str):
            raise HTTPException(status_code=400, detail="request_ids must be strings")
        value = request_id.strip()
        if not value:
            raise HTTPException(status_code=400, detail="request_ids contains empty value")
        normalized.append(value)
    if not normalized:
        raise HTTPException(status_code=400, detail="request_ids list required")
    if len(normalized) > C12_MAX_BATCH_REQUEST_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"request_ids exceeds max count: {C12_MAX_BATCH_REQUEST_IDS}",
        )
    return normalized


def _normalize_export_format(fmt: str) -> str:
    normalized = (fmt or "").strip().lower()
    if normalized not in {"json", "csv", "markdown"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")
    return normalized


@approval_request_router.post("/requests")
async def create_approval_request(
    req: ApprovalRequestCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    try:
        areq = svc.create_request(
            title=req.title,
            category_id=req.category_id,
            entity_type=req.entity_type,
            entity_id=req.entity_id,
            priority=req.priority,
            description=req.description,
            assigned_to_id=req.assigned_to_id,
            user_id=user_id,
            properties=req.properties,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _request_dict(areq)


@approval_request_router.post("/requests/{request_id}/transition")
async def transition_approval_request(
    request_id: str,
    req: ApprovalTransitionRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    try:
        areq = svc.transition_request(
            request_id,
            target_state=req.target_state,
            rejection_reason=req.rejection_reason,
            decided_by_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _request_dict(areq)


@approval_request_router.get("/requests")
async def list_approval_requests(
    state: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    reqs = svc.list_requests(
        state=state,
        category_id=category_id,
        entity_type=entity_type,
        entity_id=entity_id,
        priority=priority,
        assigned_to_id=assigned_to_id,
    )
    return {"total": len(reqs), "requests": [_request_dict(r) for r in reqs]}


@approval_request_router.get("/requests/export")
async def export_approval_requests(
    format: str = Query("json"),
    state: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    normalized_format = _normalize_export_format(format)
    svc = ApprovalService(db)
    try:
        payload = svc.export_requests(
            fmt=normalized_format,
            state=state,
            category_id=category_id,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
            assigned_to_id=assigned_to_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(
        payload=payload,
        fmt=normalized_format,
        stem="approval-requests-export",
    )


@approval_request_router.get("/requests/{request_id}/lifecycle")
async def get_approval_request_lifecycle(
    request_id: str,
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    try:
        return svc.get_request_lifecycle(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@approval_request_router.get("/requests/{request_id}/consumer-summary")
async def get_approval_request_consumer_summary(
    request_id: str,
    include_history: bool = Query(False),
    history_limit: int = Query(C12_DEFAULT_HISTORY_LIMIT, ge=1, le=200),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    try:
        payload = svc.get_request_consumer_summary(
            request_id,
            include_history=include_history,
            history_limit=history_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    payload["urls"] = {
        "detail": f"/api/v1/approvals/requests/{request_id}",
        "transition": f"/api/v1/approvals/requests/{request_id}/transition",
        "lifecycle": f"/api/v1/approvals/requests/{request_id}/lifecycle",
        "history": f"/api/v1/approvals/requests/{request_id}/history",
    }
    return payload


@approval_request_router.get("/requests/{request_id}/history")
async def get_approval_request_history(
    request_id: str,
    history_limit: int = Query(C12_DEFAULT_HISTORY_LIMIT, ge=1, le=200),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    try:
        return svc.get_request_history(request_id, limit=history_limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@approval_request_router.post("/requests/pack-summary")
async def approval_request_pack_summary(
    payload: ApprovalBatchRequest,
    include_history: bool = Query(False),
    history_limit: int = Query(C12_DEFAULT_HISTORY_LIMIT, ge=1, le=200),
    db: Session = Depends(get_db),
):
    request_ids = _normalize_batch_request_ids(payload.request_ids)
    svc = ApprovalService(db)
    rows = [
        svc.get_request_pack_row(
            request_id,
            include_history=include_history,
            history_limit=history_limit,
        )
        for request_id in request_ids
    ]
    found_rows = [row for row in rows if row["found"]]
    return {
        "requested_count": len(request_ids),
        "found_count": len(found_rows),
        "not_found_count": len(request_ids) - len(found_rows),
        "pending_count": sum(1 for row in found_rows if row["state"] == "pending"),
        "terminal_count": sum(1 for row in found_rows if row["status"] and row["status"]["is_terminal"]),
        "unassigned_pending_count": sum(
            1
            for row in found_rows
            if row["state"] == "pending" and row["assigned_to_id"] is None
        ),
        "generated_at": ApprovalService._utcnow_iso(),
        "requests": rows,
    }


@approval_request_router.get("/requests/{request_id}")
async def get_approval_request(request_id: str, db: Session = Depends(get_db)):
    svc = ApprovalService(db)
    areq = svc.get_request(request_id)
    if not areq:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return _request_dict(areq)
