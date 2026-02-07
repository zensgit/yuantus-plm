from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.baseline import Baseline, BaselineComparison, BaselineMember
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.baseline_service import BaselineService
from yuantus.meta_engine.web.release_diagnostics_models import (
    ReleaseDiagnosticsResponse,
    issue_to_response,
)

baseline_router = APIRouter(prefix="/baselines", tags=["Baselines"])


class BaselineCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    root_item_id: Optional[str] = None
    root_version_id: Optional[str] = None
    baseline_type: str = Field(default="bom", max_length=50)
    scope: str = Field(default="product", max_length=50)
    baseline_number: Optional[str] = Field(default=None, max_length=60)
    eco_id: Optional[str] = None
    max_levels: int = Field(default=10, ge=-1, le=50)
    bom_levels: Optional[int] = Field(default=None, ge=-1, le=50)
    effective_at: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    include_bom: Optional[bool] = None
    include_substitutes: bool = False
    include_effectivity: bool = False
    include_documents: Optional[bool] = None
    include_relationships: Optional[bool] = None
    line_key: str = Field(default="child_config", min_length=1, max_length=50)
    auto_populate: bool = True
    state: Optional[str] = Field(default=None, max_length=50)


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
    baseline_number: Optional[str]
    scope: Optional[str]
    eco_id: Optional[str]
    root_item_id: Optional[str]
    root_version_id: Optional[str]
    root_config_id: Optional[str]
    max_levels: int
    bom_levels: Optional[int]
    effective_at: Optional[datetime]
    effective_date: Optional[datetime]
    include_bom: Optional[bool]
    include_substitutes: bool
    include_effectivity: bool
    include_documents: Optional[bool]
    include_relationships: Optional[bool]
    line_key: str
    item_count: int
    relationship_count: int
    state: Optional[str]
    is_validated: Optional[bool]
    validation_errors: Optional[Dict[str, Any]] = None
    validated_at: Optional[datetime]
    validated_by_id: Optional[int]
    is_locked: Optional[bool]
    locked_at: Optional[datetime]
    released_at: Optional[datetime]
    released_by_id: Optional[int]
    created_at: Optional[datetime]
    created_by_id: Optional[int]
    snapshot: Optional[Dict[str, Any]] = None


class BaselineMemberResponse(BaseModel):
    id: str
    baseline_id: str
    member_type: str
    item_id: Optional[str] = None
    document_id: Optional[str] = None
    relationship_id: Optional[str] = None
    item_number: Optional[str] = None
    item_revision: Optional[str] = None
    item_generation: Optional[int] = None
    item_type: Optional[str] = None
    level: int
    path: Optional[str] = None
    quantity: Optional[str] = None
    item_state: Optional[str] = None


class BaselineReleaseRequest(BaseModel):
    force: bool = False


class BaselineCompareBaselinesRequest(BaseModel):
    baseline_a_id: str = Field(..., min_length=1)
    baseline_b_id: str = Field(..., min_length=1)


def _is_admin(user: CurrentUser) -> bool:
    roles = set(user.roles or [])
    return "admin" in roles or "superuser" in roles


def _ensure_can_access_baseline(
    service: BaselineService,
    baseline: Baseline,
    *,
    user: CurrentUser,
    db: Session,
) -> None:
    """Enforce baseline read access consistent with get_baseline/list_members."""
    if _is_admin(user):
        return
    if baseline.created_by_id == user.id:
        return

    if baseline.root_item_id:
        item = db.get(Item, baseline.root_item_id)
        if item:
            try:
                service._ensure_can_read(item, str(user.id), list(user.roles or []))
                return
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=exc.to_dict()) from exc

    raise HTTPException(status_code=403, detail="Permission denied")


def _baseline_to_response(
    baseline: Baseline, *, include_snapshot: bool
) -> BaselineResponse:
    return BaselineResponse(
        id=baseline.id,
        name=baseline.name,
        description=baseline.description,
        baseline_type=baseline.baseline_type,
        baseline_number=baseline.baseline_number,
        scope=baseline.scope,
        eco_id=baseline.eco_id,
        root_item_id=baseline.root_item_id,
        root_version_id=baseline.root_version_id,
        root_config_id=baseline.root_config_id,
        max_levels=baseline.max_levels,
        bom_levels=baseline.max_levels,
        effective_at=baseline.effective_at,
        effective_date=baseline.effective_at,
        include_bom=baseline.include_bom,
        include_substitutes=bool(baseline.include_substitutes),
        include_effectivity=bool(baseline.include_effectivity),
        include_documents=baseline.include_documents,
        include_relationships=baseline.include_relationships,
        line_key=baseline.line_key,
        item_count=baseline.item_count or 0,
        relationship_count=baseline.relationship_count or 0,
        state=baseline.state,
        is_validated=baseline.is_validated,
        validation_errors=baseline.validation_errors,
        validated_at=baseline.validated_at,
        validated_by_id=baseline.validated_by_id,
        is_locked=baseline.is_locked,
        locked_at=baseline.locked_at,
        released_at=baseline.released_at,
        released_by_id=baseline.released_by_id,
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
            max_levels=req.bom_levels if req.bom_levels is not None else req.max_levels,
            effective_at=req.effective_at,
            include_substitutes=req.include_substitutes,
            include_effectivity=req.include_effectivity,
            line_key=req.line_key,
            created_by_id=user.id,
            roles=list(user.roles or []),
            baseline_type=req.baseline_type,
            scope=req.scope,
            baseline_number=req.baseline_number,
            effective_date=req.effective_date,
            include_bom=req.include_bom,
            include_documents=req.include_documents,
            include_relationships=req.include_relationships,
            bom_levels=req.bom_levels,
            eco_id=req.eco_id,
            auto_populate=req.auto_populate,
            state=req.state,
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
    baseline_type: Optional[str] = Query(None, max_length=50),
    scope: Optional[str] = Query(None, max_length=50),
    state: Optional[str] = Query(None, max_length=50),
    effective_from: Optional[datetime] = Query(None),
    effective_to: Optional[datetime] = Query(None),
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
        baseline_type=baseline_type,
        scope=scope,
        state=state,
        effective_from=effective_from,
        effective_to=effective_to,
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


@baseline_router.get("/effective", response_model=BaselineResponse)
def get_effective_baseline(
    root_item_id: str = Query(..., min_length=1),
    target_date: datetime = Query(...),
    baseline_type: Optional[str] = Query(None),
    include_snapshot: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    baseline = service.get_baseline_at_date(
        root_item_id=root_item_id,
        target_date=target_date,
        baseline_type=baseline_type,
    )
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    if not _is_admin(user) and baseline.created_by_id != user.id:
        if baseline.root_item_id:
            item = db.get(Item, baseline.root_item_id)
            if item:
                try:
                    service._ensure_can_read(item, str(user.id), user.roles or [])
                except PermissionError as exc:
                    raise HTTPException(status_code=403, detail=str(exc)) from exc

    return _baseline_to_response(baseline, include_snapshot=include_snapshot)


@baseline_router.post("/compare-baselines", response_model=Dict[str, Any])
def compare_baselines(
    req: BaselineCompareBaselinesRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = BaselineService(db)
    baseline_a = service.get_baseline(req.baseline_a_id)
    baseline_b = service.get_baseline(req.baseline_b_id)
    if not baseline_a or not baseline_b:
        raise HTTPException(status_code=404, detail="Baseline not found")

    _ensure_can_access_baseline(service, baseline_a, user=user, db=db)
    _ensure_can_access_baseline(service, baseline_b, user=user, db=db)

    return service.compare_baselines(
        baseline_a_id=req.baseline_a_id,
        baseline_b_id=req.baseline_b_id,
        user_id=user.id,
    )


@baseline_router.get("/comparisons/{comparison_id}/details", response_model=Dict[str, Any])
def get_comparison_details(
    comparison_id: str,
    change_type: Optional[str] = Query(None, description="added|removed|changed"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = BaselineService(db)
    comparison = db.get(BaselineComparison, comparison_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Baseline comparison not found")

    baseline_a = service.get_baseline(comparison.baseline_a_id)
    baseline_b = service.get_baseline(comparison.baseline_b_id)
    if not baseline_a or not baseline_b:
        raise HTTPException(status_code=404, detail="Baseline not found")

    _ensure_can_access_baseline(service, baseline_a, user=user, db=db)
    _ensure_can_access_baseline(service, baseline_b, user=user, db=db)

    try:
        return service.get_comparison_details(
            comparison_id=comparison_id,
            change_type=change_type,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@baseline_router.get("/comparisons/{comparison_id}/export")
def export_comparison_details(
    comparison_id: str,
    export_format: str = Query("csv"),
    change_type: Optional[str] = Query(None, description="added|removed|changed"),
    limit: int = Query(2000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service = BaselineService(db)
    comparison = db.get(BaselineComparison, comparison_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Baseline comparison not found")

    baseline_a = service.get_baseline(comparison.baseline_a_id)
    baseline_b = service.get_baseline(comparison.baseline_b_id)
    if not baseline_a or not baseline_b:
        raise HTTPException(status_code=404, detail="Baseline not found")

    _ensure_can_access_baseline(service, baseline_a, user=user, db=db)
    _ensure_can_access_baseline(service, baseline_b, user=user, db=db)

    try:
        result = service.export_comparison_details(
            comparison_id=comparison_id,
            change_type=change_type,
            export_format=export_format,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"baseline_comparison_{comparison_id}.{result['extension']}"
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers=headers,
    )


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


@baseline_router.get("/{baseline_id}/members", response_model=Dict[str, Any])
def list_baseline_members(
    baseline_id: str,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = BaselineService(db)
    baseline = service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    _ensure_can_access_baseline(service, baseline, user=user, db=db)

    q = db.query(BaselineMember).filter(BaselineMember.baseline_id == baseline_id)
    total = q.count()
    # Stable pagination: order by level then path/id.
    members = (
        q.order_by(
            BaselineMember.level.asc(),
            func.coalesce(BaselineMember.path, "").asc(),
            BaselineMember.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "items": [
            BaselineMemberResponse(
                id=m.id,
                baseline_id=m.baseline_id,
                member_type=m.member_type,
                item_id=m.item_id,
                document_id=m.document_id,
                relationship_id=m.relationship_id,
                item_number=m.item_number,
                item_revision=m.item_revision,
                item_generation=m.item_generation,
                item_type=m.item_type,
                level=m.level,
                path=m.path,
                quantity=m.quantity,
                item_state=m.item_state,
            ).model_dump()
            for m in members
        ],
    }


@baseline_router.post("/{baseline_id}/validate", response_model=Dict[str, Any])
def validate_baseline(
    baseline_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = BaselineService(db)
    baseline = service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    _ensure_can_access_baseline(service, baseline, user=user, db=db)
    try:
        return service.validate_baseline(baseline_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@baseline_router.get(
    "/{baseline_id}/release-diagnostics",
    response_model=ReleaseDiagnosticsResponse,
)
def get_baseline_release_diagnostics(
    baseline_id: str,
    ruleset_id: str = Query("default"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReleaseDiagnosticsResponse:
    service = BaselineService(db)
    baseline = service.get_baseline(baseline_id)
    if baseline:
        _ensure_can_access_baseline(service, baseline, user=user, db=db)
    try:
        diagnostics = service.get_release_diagnostics(baseline_id, ruleset_id=ruleset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    errors = [issue_to_response(issue) for issue in (diagnostics.get("errors") or [])]
    warnings = [issue_to_response(issue) for issue in (diagnostics.get("warnings") or [])]
    return ReleaseDiagnosticsResponse(
        ok=len(errors) == 0,
        resource_type="baseline",
        resource_id=baseline_id,
        ruleset_id=str(diagnostics.get("ruleset_id") or ruleset_id),
        errors=errors,
        warnings=warnings,
    )


@baseline_router.post("/{baseline_id}/release", response_model=BaselineResponse)
def release_baseline(
    baseline_id: str,
    req: BaselineReleaseRequest,
    ruleset_id: str = Query("default"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BaselineResponse:
    service = BaselineService(db)
    baseline = service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    _ensure_can_access_baseline(service, baseline, user=user, db=db)

    if not req.force:
        try:
            diagnostics = service.get_release_diagnostics(baseline_id, ruleset_id=ruleset_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        err_count = len(diagnostics.get("errors") or [])
        warn_count = len(diagnostics.get("warnings") or [])
        if err_count:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Baseline release blocked: errors={err_count}, warnings={warn_count}. "
                    f"Run /api/v1/baselines/{baseline_id}/release-diagnostics?ruleset_id={ruleset_id} for details."
                ),
            )

    try:
        baseline = service.release_baseline(
            baseline_id,
            user_id=user.id,
            force=req.force,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _baseline_to_response(baseline, include_snapshot=True)


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
    _ensure_can_access_baseline(service, baseline, user=user, db=db)

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
    elif req.target_type == "baseline":
        target_baseline = service.get_baseline(req.target_id)
        if not target_baseline:
            raise HTTPException(status_code=404, detail="Target baseline not found")
        _ensure_can_access_baseline(service, target_baseline, user=user, db=db)

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
