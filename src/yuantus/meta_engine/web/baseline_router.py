from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.baseline import Baseline
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.baseline_service import BaselineService

baseline_router = APIRouter(prefix="/baselines", tags=["Baselines"])


class BaselineCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    root_item_id: Optional[str] = None
    root_version_id: Optional[str] = None
    max_levels: int = Field(default=10, ge=-1, le=50)
    effective_at: Optional[datetime] = None
    include_substitutes: bool = False
    include_effectivity: bool = False
    line_key: str = Field(default="child_config", min_length=1, max_length=50)


class BaselineCompareRequest(BaseModel):
    target_type: str = Field(..., description="item|version|baseline")
    target_id: str = Field(..., min_length=1)
    max_levels: int = Field(default=10, ge=-1, le=50)
    effective_at: Optional[datetime] = None
    include_substitutes: bool = False
    include_effectivity: bool = False
    include_child_fields: bool = False
    include_relationship_props: Optional[List[str]] = None
    line_key: Optional[str] = None


class BaselineResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    baseline_type: str
    root_item_id: Optional[str]
    root_version_id: Optional[str]
    root_config_id: Optional[str]
    max_levels: int
    effective_at: Optional[datetime]
    include_substitutes: bool
    include_effectivity: bool
    line_key: str
    item_count: int
    relationship_count: int
    created_at: Optional[datetime]
    created_by_id: Optional[int]
    snapshot: Optional[Dict[str, Any]] = None


def _is_admin(user: CurrentUser) -> bool:
    roles = set(user.roles or [])
    return "admin" in roles or "superuser" in roles


def _baseline_to_response(
    baseline: Baseline, *, include_snapshot: bool
) -> BaselineResponse:
    return BaselineResponse(
        id=baseline.id,
        name=baseline.name,
        description=baseline.description,
        baseline_type=baseline.baseline_type,
        root_item_id=baseline.root_item_id,
        root_version_id=baseline.root_version_id,
        root_config_id=baseline.root_config_id,
        max_levels=baseline.max_levels,
        effective_at=baseline.effective_at,
        include_substitutes=bool(baseline.include_substitutes),
        include_effectivity=bool(baseline.include_effectivity),
        line_key=baseline.line_key,
        item_count=baseline.item_count or 0,
        relationship_count=baseline.relationship_count or 0,
        created_at=baseline.created_at,
        created_by_id=baseline.created_by_id,
        snapshot=baseline.snapshot if include_snapshot else None,
    )


@baseline_router.post("", response_model=BaselineResponse)
def create_baseline(
    req: BaselineCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BaselineResponse:
    if not req.root_item_id and not req.root_version_id:
        raise HTTPException(status_code=400, detail="root_item_id or root_version_id required")

    service = BaselineService(db)
    try:
        baseline = service.create_baseline(
            name=req.name,
            description=req.description,
            root_item_id=req.root_item_id,
            root_version_id=req.root_version_id,
            max_levels=req.max_levels,
            effective_at=req.effective_at,
            include_substitutes=req.include_substitutes,
            include_effectivity=req.include_effectivity,
            line_key=req.line_key,
            created_by_id=user.id,
            roles=list(user.roles or []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc

    return _baseline_to_response(baseline, include_snapshot=True)


@baseline_router.get("", response_model=Dict[str, Any])
def list_baselines(
    root_item_id: Optional[str] = Query(None),
    root_version_id: Optional[str] = Query(None),
    created_by_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_snapshot: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = BaselineService(db)
    effective_created_by = created_by_id
    if not _is_admin(user):
        effective_created_by = user.id

    items, total = service.list_baselines(
        root_item_id=root_item_id,
        root_version_id=root_version_id,
        created_by_id=effective_created_by,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "items": [
            _baseline_to_response(item, include_snapshot=include_snapshot).model_dump()
            for item in items
        ],
    }


@baseline_router.get("/{baseline_id}", response_model=BaselineResponse)
def get_baseline(
    baseline_id: str,
    include_snapshot: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BaselineResponse:
    service = BaselineService(db)
    baseline = service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    if not _is_admin(user) and baseline.created_by_id != user.id:
        if baseline.root_item_id:
            item = db.get(Item, baseline.root_item_id)
            if item:
                try:
                    service._ensure_can_read(item, str(user.id), list(user.roles or []))
                except PermissionError as exc:
                    raise HTTPException(status_code=403, detail=exc.to_dict()) from exc
            else:
                raise HTTPException(status_code=403, detail="Permission denied")
        else:
            raise HTTPException(status_code=403, detail="Permission denied")

    return _baseline_to_response(baseline, include_snapshot=include_snapshot)


@baseline_router.post("/{baseline_id}/compare", response_model=Dict[str, Any])
def compare_baseline(
    baseline_id: str,
    req: BaselineCompareRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = BaselineService(db)
    baseline = service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    # Permission guard for target items
    if req.target_type == "item":
        target = db.get(Item, req.target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target item not found")
        try:
            service._ensure_can_read(target, str(user.id), list(user.roles or []))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=exc.to_dict()) from exc
    elif req.target_type == "version":
        from yuantus.meta_engine.version.models import ItemVersion

        ver = db.get(ItemVersion, req.target_id)
        if not ver:
            raise HTTPException(status_code=404, detail="Target version not found")
        target = db.get(Item, ver.item_id)
        if target:
            try:
                service._ensure_can_read(target, str(user.id), list(user.roles or []))
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=exc.to_dict()) from exc

    try:
        result = service.compare_baseline(
            baseline=baseline,
            target_type=req.target_type,
            target_id=req.target_id,
            max_levels=req.max_levels,
            effective_at=req.effective_at,
            include_substitutes=req.include_substitutes,
            include_effectivity=req.include_effectivity,
            include_child_fields=req.include_child_fields,
            include_relationship_props=req.include_relationship_props,
            line_key=req.line_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result
