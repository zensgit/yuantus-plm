from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.impact_analysis_service import (
    CurrentUserView,
    ImpactAnalysisService,
)
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService


impact_router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


class WhereUsedHit(BaseModel):
    parent_id: Optional[str] = None
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    relationship_id: Optional[str] = None
    level: int = 1
    line: Dict[str, Any] = Field(default_factory=dict)


class WhereUsedSummary(BaseModel):
    total: int
    hits: List[WhereUsedHit] = Field(default_factory=list)
    recursive: bool
    max_levels: int


class BaselineHit(BaseModel):
    baseline_id: str
    name: str
    baseline_number: Optional[str] = None
    baseline_type: Optional[str] = None
    scope: Optional[str] = None
    state: Optional[str] = None
    root_item_id: Optional[str] = None
    created_at: Optional[datetime] = None
    released_at: Optional[datetime] = None


class BaselinesSummary(BaseModel):
    total: int
    hits: List[BaselineHit] = Field(default_factory=list)


class SignatureHit(BaseModel):
    id: str
    meaning: str
    status: str
    signed_at: Optional[datetime] = None
    signer_username: Optional[str] = None


class ESignManifestSummary(BaseModel):
    id: str
    generation: int
    is_complete: bool
    completed_at: Optional[datetime] = None


class ESignSummary(BaseModel):
    total: int
    valid: int
    revoked: int
    expired: int
    latest_signed_at: Optional[datetime] = None
    latest_signatures: List[SignatureHit] = Field(default_factory=list)
    latest_manifest: Optional[ESignManifestSummary] = None


class ImpactSummaryResponse(BaseModel):
    item_id: str
    generated_at: datetime
    where_used: WhereUsedSummary
    baselines: BaselinesSummary
    esign: ESignSummary


@impact_router.get("/items/{item_id}/summary", response_model=ImpactSummaryResponse)
def get_item_impact_summary(
    item_id: str,
    where_used_recursive: bool = Query(False, description="Include ancestors recursively"),
    where_used_max_levels: int = Query(10, ge=1, le=50),
    where_used_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    signature_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImpactSummaryResponse:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        item.item_type_id,
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = ImpactAnalysisService(db)
    user_view = CurrentUserView(
        id=int(user.id),
        roles=list(user.roles or []),
        is_superuser=bool(getattr(user, "is_superuser", False)),
    )

    where_used = service.where_used_summary(
        item_id=item_id,
        recursive=where_used_recursive,
        max_levels=where_used_max_levels,
        limit=where_used_limit,
    )
    baselines = service.baselines_summary(
        item_id=item_id,
        user=user_view,
        limit=baseline_limit,
    )
    esign = service.esign_summary(item_id=item_id, limit=signature_limit)

    return ImpactSummaryResponse(
        item_id=item_id,
        generated_at=datetime.utcnow(),
        where_used=WhereUsedSummary(**where_used),
        baselines=BaselinesSummary(**baselines),
        esign=ESignSummary(**esign),
    )

