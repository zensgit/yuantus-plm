from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.services.spare_service import SPARE_ITEM_TYPE, SpareService


spare_router = APIRouter(prefix="/items", tags=["Item Spares"])


class AddSpareRequest(BaseModel):
    """Request body for designating a spare part."""

    spare_item_id: str = Field(..., description="ID of the spare-part Part")
    properties: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Optional relationship properties. Conventional keys (free-form, "
            "not enforced): quantity (consumers treat absent as 1), "
            "position/ref, notes."
        ),
    )


class AddSpareResponse(BaseModel):
    """Response for add spare operation."""

    ok: bool
    spare_id: str
    item_id: str
    spare_item_id: str
    properties: Optional[Dict[str, Any]] = None


class RemoveSpareResponse(BaseModel):
    """Response for remove spare operation."""

    ok: bool
    spare_id: str


class SpareEntry(BaseModel):
    """A single spare-part entry."""

    id: str
    spare_item_id: Optional[str]
    spare_part: Optional[Dict[str, Any]] = None
    relationship: Dict[str, Any]


class SpareListResponse(BaseModel):
    """Response for listing the direct spares of a Part."""

    item_id: str
    count: int
    spares: List[SpareEntry]


class SpareExplodeGroup(BaseModel):
    """Spares grouped under one part of the exploded assembly."""

    item_id: str
    count: int
    spares: List[SpareEntry]


class SpareExplodeResponse(BaseModel):
    """Response for the exploded spare-parts view down an assembly."""

    item_id: str
    levels: int
    count: int
    groups: List[SpareExplodeGroup]


@spare_router.get(
    "/{item_id}/spares",
    response_model=SpareListResponse,
    summary="List spare parts for a Part",
)
async def list_spares(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    if item.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Invalid Part type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        SPARE_ITEM_TYPE,
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = SpareService(db, user_id=str(user.id), roles=user.roles)
    spares = service.list_spares(item_id)
    return SpareListResponse(
        item_id=item_id,
        count=len(spares),
        spares=spares,
    )


@spare_router.post(
    "/{item_id}/spares",
    response_model=AddSpareResponse,
    summary="Add a spare part to a Part",
)
async def add_spare(
    item_id: str,
    request: AddSpareRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if item_id == request.spare_item_id:
        raise HTTPException(status_code=400, detail="Item cannot be a spare of itself")

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    if item.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Invalid Part type")

    spare_item = db.get(Item, request.spare_item_id)
    if not spare_item:
        raise HTTPException(
            status_code=404,
            detail=f"Item {request.spare_item_id} not found",
        )
    if spare_item.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Invalid Part type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        SPARE_ITEM_TYPE,
        AMLAction.add,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        "Part",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = SpareService(db, user_id=str(user.id), roles=user.roles)
    try:
        rel = service.add_spare(
            item_id=item_id,
            spare_item_id=request.spare_item_id,
            properties=request.properties,
            user_id=int(user.id),
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "Invalid Part" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return AddSpareResponse(
        ok=True,
        spare_id=rel.id,
        item_id=item_id,
        spare_item_id=request.spare_item_id,
        properties=request.properties,
    )


@spare_router.delete(
    "/{item_id}/spares/{spare_id}",
    response_model=RemoveSpareResponse,
    summary="Remove a spare relationship",
)
async def remove_spare(
    item_id: str,
    spare_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rel = db.get(Item, spare_id)
    if not rel or rel.item_type_id != SPARE_ITEM_TYPE:
        raise HTTPException(status_code=404, detail="Spare relationship not found")
    # Directional: the spare hangs off the assembly (source side).
    if rel.source_id != item_id:
        raise HTTPException(status_code=404, detail="Spare relationship not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        SPARE_ITEM_TYPE,
        AMLAction.delete,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = SpareService(db, user_id=str(user.id), roles=user.roles)
    try:
        service.remove_spare(spare_id, user_id=int(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RemoveSpareResponse(ok=True, spare_id=spare_id)


@spare_router.get(
    "/{item_id}/spares/explode",
    response_model=SpareExplodeResponse,
    summary="Exploded spare-parts view down an assembly",
)
async def explode_spares(
    item_id: str,
    levels: int = Query(10, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    if item.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Invalid Part type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        SPARE_ITEM_TYPE,
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = SpareService(db, user_id=str(user.id), roles=user.roles)
    try:
        groups = service.explode_spares(item_id, levels=levels)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    total = sum(g["count"] for g in groups)
    return SpareExplodeResponse(
        item_id=item_id,
        levels=levels,
        count=total,
        groups=groups,
    )
