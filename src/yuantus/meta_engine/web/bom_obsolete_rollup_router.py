from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_obsolete_service import BOMObsoleteService
from yuantus.meta_engine.services.bom_rollup_service import BOMRollupService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService

bom_obsolete_rollup_router = APIRouter(prefix="/bom", tags=["BOM"])


class ObsoleteScanEntry(BaseModel):
    """Single obsolete BOM line entry."""

    relationship_id: str
    relationship_type: str
    parent_id: Optional[str]
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    child_id: Optional[str]
    child_number: Optional[str] = None
    child_name: Optional[str] = None
    child_state: Optional[str] = None
    child_is_current: Optional[bool] = None
    replacement_id: Optional[str] = None
    replacement_number: Optional[str] = None
    replacement_name: Optional[str] = None
    level: int
    reasons: List[str]


class ObsoleteScanResponse(BaseModel):
    """Response for obsolete BOM scan."""

    root_id: str
    count: int
    entries: List[ObsoleteScanEntry]


class ObsoleteResolveRequest(BaseModel):
    """Resolve obsolete BOM lines."""

    mode: str = Field("update", description="update or new_bom")
    recursive: bool = Field(True, description="Scan descendants")
    levels: int = Field(10, description="Max scan depth (-1 for unlimited)")
    relationship_types: Optional[List[str]] = Field(
        None, description="Relationship item types to scan"
    )
    dry_run: bool = Field(False, description="Return plan only")


class ObsoleteResolveResponse(BaseModel):
    """Response for obsolete BOM resolution."""

    ok: bool
    mode: str
    root_id: str
    summary: Dict[str, Any]
    entries: List[Dict[str, Any]]


class WeightRollupRequest(BaseModel):
    """Request for BOM weight rollup."""

    levels: int = Field(10, description="Explosion depth")
    effective_date: Optional[datetime] = Field(None, description="Effectivity date")
    lot_number: Optional[str] = Field(None, description="Lot number for effectivity")
    serial_number: Optional[str] = Field(None, description="Serial number for effectivity")
    unit_position: Optional[str] = Field(None, description="Unit position for effectivity")
    write_back: bool = Field(False, description="Persist computed weights")
    write_back_field: str = Field("weight_rollup", description="Target property name")
    write_back_mode: str = Field("missing", description="missing or overwrite")
    rounding: Optional[int] = Field(3, description="Rounding precision (None to skip)")


@bom_obsolete_rollup_router.get("/{item_id}/obsolete", response_model=ObsoleteScanResponse)
async def get_obsolete_bom(
    item_id: str,
    recursive: bool = Query(True, description="Scan descendants"),
    levels: int = Query(10, description="Max scan depth (-1 for unlimited)"),
    relationship_types: Optional[str] = Query(
        None, description="Comma-separated relationship types"
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    root = db.get(Item, item_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        root.item_type_id,
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

    rel_types = (
        [t.strip() for t in relationship_types.split(",") if t.strip()]
        if relationship_types
        else None
    )

    service = BOMObsoleteService(db)
    return service.scan(
        item_id,
        recursive=recursive,
        max_levels=levels,
        relationship_types=rel_types,
    )


@bom_obsolete_rollup_router.post("/{item_id}/obsolete/resolve", response_model=ObsoleteResolveResponse)
async def resolve_obsolete_bom(
    item_id: str,
    request: ObsoleteResolveRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    root = db.get(Item, item_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM",
        AMLAction.update,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    if request.mode.lower().strip() == "new_bom":
        if not perm.check_permission(
            "Part BOM",
            AMLAction.add,
            user_id=str(user.id),
            user_roles=user.roles,
        ):
            raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMObsoleteService(db)
    try:
        result = service.resolve(
            item_id,
            mode=request.mode,
            recursive=request.recursive,
            max_levels=request.levels,
            relationship_types=request.relationship_types,
            dry_run=request.dry_run,
            user_id=int(user.id) if user.id else None,
        )
        if request.dry_run:
            db.rollback()
        else:
            db.commit()
        return result
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@bom_obsolete_rollup_router.post("/{item_id}/rollup/weight", response_model=Dict[str, Any])
async def rollup_bom_weight(
    item_id: str,
    request: WeightRollupRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    root = db.get(Item, item_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        root.item_type_id,
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    if request.write_back and not perm.check_permission(
        root.item_type_id,
        AMLAction.update,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMRollupService(db)
    result = service.compute_weight_rollup(
        item_id,
        levels=request.levels,
        effective_date=request.effective_date,
        lot_number=request.lot_number,
        serial_number=request.serial_number,
        unit_position=request.unit_position,
        write_back=request.write_back,
        write_back_field=request.write_back_field,
        write_back_mode=request.write_back_mode,
        rounding=request.rounding,
    )
    if request.write_back:
        db.commit()
    return result
