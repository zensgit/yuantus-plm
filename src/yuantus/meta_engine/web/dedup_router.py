from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.dedup.models import (
    DedupBatch,
    DedupBatchStatus,
    DedupRule,
    SimilarityRecord,
    SimilarityStatus,
)
from yuantus.meta_engine.dedup.service import DedupService


dedup_router = APIRouter(prefix="/dedup", tags=["Dedup"])


class DedupRuleCreate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    document_type: Optional[str] = None
    phash_threshold: int = 10
    feature_threshold: float = 0.85
    combined_threshold: float = 0.80
    detection_mode: str = "balanced"
    auto_create_relationship: bool = False
    auto_trigger_workflow: bool = False
    workflow_map_id: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None
    priority: int = 100
    is_active: bool = True


class DedupRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    document_type: Optional[str] = None
    phash_threshold: Optional[int] = None
    feature_threshold: Optional[float] = None
    combined_threshold: Optional[float] = None
    detection_mode: Optional[str] = None
    auto_create_relationship: Optional[bool] = None
    auto_trigger_workflow: Optional[bool] = None
    workflow_map_id: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class DedupRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    item_type_id: Optional[str]
    document_type: Optional[str]
    phash_threshold: int
    feature_threshold: float
    combined_threshold: float
    detection_mode: str
    auto_create_relationship: bool
    auto_trigger_workflow: bool
    workflow_map_id: Optional[str]
    exclude_patterns: List[str]
    priority: int
    is_active: bool
    created_at: Optional[datetime]
    created_by_id: Optional[int]
    updated_at: Optional[datetime]


class SimilarityRecordResponse(BaseModel):
    id: str
    source_file_id: str
    target_file_id: str
    similarity_score: float
    similarity_type: Optional[str]
    detection_method: Optional[str]
    detection_params: Optional[Dict[str, Any]]
    status: str
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    review_comment: Optional[str]
    relationship_item_id: Optional[str]
    batch_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SimilarityReviewRequest(BaseModel):
    status: str = Field(..., description="pending|confirmed|rejected|merged|ignored")
    comment: Optional[str] = None
    create_relationship: bool = False


class DedupBatchCreate(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    scope_type: str = "all"
    scope_config: Optional[Dict[str, Any]] = None
    rule_id: Optional[str] = None


class DedupBatchResponse(BaseModel):
    id: str
    name: Optional[str]
    description: Optional[str]
    scope_type: str
    scope_config: Optional[Dict[str, Any]]
    rule_id: Optional[str]
    status: str
    total_files: int
    processed_files: int
    found_similarities: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    summary: Optional[Dict[str, Any]]
    created_at: Optional[datetime]
    created_by_id: Optional[int]


class DedupBatchRunRequest(BaseModel):
    mode: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1, le=5000)
    priority: int = Field(default=30, ge=1, le=100)
    dedupe: bool = True
    index: bool = False
    rule_id: Optional[str] = None


class DedupBatchRunResponse(BaseModel):
    batch: DedupBatchResponse
    jobs_created: int


def _ensure_admin(user: CurrentUser) -> None:
    roles = set(user.roles or [])
    if "admin" in roles or "superuser" in roles or user.is_superuser:
        return
    raise HTTPException(status_code=403, detail="Admin required")


def _rule_to_response(rule: DedupRule) -> DedupRuleResponse:
    return DedupRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        item_type_id=rule.item_type_id,
        document_type=rule.document_type,
        phash_threshold=rule.phash_threshold,
        feature_threshold=rule.feature_threshold,
        combined_threshold=rule.combined_threshold,
        detection_mode=rule.detection_mode,
        auto_create_relationship=bool(rule.auto_create_relationship),
        auto_trigger_workflow=bool(rule.auto_trigger_workflow),
        workflow_map_id=rule.workflow_map_id,
        exclude_patterns=list(rule.exclude_patterns or []),
        priority=rule.priority or 100,
        is_active=bool(rule.is_active),
        created_at=rule.created_at,
        created_by_id=rule.created_by_id,
        updated_at=rule.updated_at,
    )


def _record_to_response(record: SimilarityRecord) -> SimilarityRecordResponse:
    return SimilarityRecordResponse(
        id=record.id,
        source_file_id=record.source_file_id,
        target_file_id=record.target_file_id,
        similarity_score=record.similarity_score,
        similarity_type=record.similarity_type,
        detection_method=record.detection_method,
        detection_params=record.detection_params,
        status=record.status,
        reviewed_by_id=record.reviewed_by_id,
        reviewed_at=record.reviewed_at,
        review_comment=record.review_comment,
        relationship_item_id=record.relationship_item_id,
        batch_id=record.batch_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _batch_to_response(batch: DedupBatch) -> DedupBatchResponse:
    return DedupBatchResponse(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        scope_type=batch.scope_type,
        scope_config=batch.scope_config,
        rule_id=batch.rule_id,
        status=batch.status,
        total_files=batch.total_files or 0,
        processed_files=batch.processed_files or 0,
        found_similarities=batch.found_similarities or 0,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
        error_message=batch.error_message,
        summary=batch.summary,
        created_at=batch.created_at,
        created_by_id=batch.created_by_id,
    )


@dedup_router.get("/rules", response_model=List[DedupRuleResponse])
async def list_rules(
    include_inactive: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    return [_rule_to_response(r) for r in service.list_rules(include_inactive=include_inactive)]


@dedup_router.get("/rules/{rule_id}", response_model=DedupRuleResponse)
async def get_rule(
    rule_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_response(rule)


@dedup_router.post("/rules", response_model=DedupRuleResponse)
async def create_rule(
    request: DedupRuleCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    try:
        rule = service.create_rule(request.model_dump(), user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return _rule_to_response(rule)


@dedup_router.patch("/rules/{rule_id}", response_model=DedupRuleResponse)
async def update_rule(
    rule_id: str,
    request: DedupRuleUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    try:
        rule = service.update_rule(rule, request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return _rule_to_response(rule)


@dedup_router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    service.deactivate_rule(rule)
    db.commit()
    return {"ok": True, "rule_id": rule_id}


@dedup_router.get("/records", response_model=Dict[str, Any])
async def list_records(
    status: Optional[str] = Query(None),
    source_file_id: Optional[str] = Query(None),
    target_file_id: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    items, total = service.list_records(
        status=status,
        source_file_id=source_file_id,
        target_file_id=target_file_id,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )
    return {"total": total, "items": [_record_to_response(r).model_dump() for r in items]}


@dedup_router.get("/records/{record_id}", response_model=SimilarityRecordResponse)
async def get_record(
    record_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    record = service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return _record_to_response(record)


@dedup_router.post("/records/{record_id}/review", response_model=SimilarityRecordResponse)
async def review_record(
    record_id: str,
    request: SimilarityReviewRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    if request.status not in {s.value for s in SimilarityStatus}:
        raise HTTPException(status_code=400, detail="Invalid status")
    service = DedupService(db)
    record = service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record = service.review_record(
        record,
        status=request.status,
        reviewer_id=user.id,
        comment=request.comment,
        create_relationship=request.create_relationship,
    )
    db.commit()
    return _record_to_response(record)


@dedup_router.post("/batches", response_model=DedupBatchResponse)
async def create_batch(
    request: DedupBatchCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    batch = service.create_batch(request.model_dump(), user_id=user.id)
    db.commit()
    return _batch_to_response(batch)


@dedup_router.get("/batches", response_model=Dict[str, Any])
async def list_batches(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    q = db.query(DedupBatch)
    if status:
        q = q.filter(DedupBatch.status == status)
    total = q.count()
    items = q.order_by(DedupBatch.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_batch_to_response(b).model_dump() for b in items]}


@dedup_router.get("/batches/{batch_id}", response_model=DedupBatchResponse)
async def get_batch(
    batch_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    batch = db.get(DedupBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_response(batch)


@dedup_router.post("/batches/{batch_id}/run", response_model=DedupBatchRunResponse)
async def run_batch(
    batch_id: str,
    request: DedupBatchRunRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    batch = db.get(DedupBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if request.rule_id and request.rule_id != batch.rule_id:
        batch.rule_id = request.rule_id
    jobs_created, _ = service.run_batch(
        batch,
        user_id=user.id,
        user_name=user.username,
        mode=request.mode,
        limit=request.limit,
        priority=request.priority,
        dedupe=request.dedupe,
        index=request.index,
        rule_id=request.rule_id,
    )
    db.commit()
    return DedupBatchRunResponse(
        batch=_batch_to_response(batch),
        jobs_created=jobs_created,
    )


@dedup_router.post("/batches/{batch_id}/refresh", response_model=DedupBatchResponse)
async def refresh_batch(
    batch_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin(user)
    service = DedupService(db)
    batch = db.get(DedupBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch = service.refresh_batch(batch)
    db.commit()
    return _batch_to_response(batch)
