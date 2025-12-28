from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.equivalent_service import EquivalentService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService


equivalent_router = APIRouter(prefix="/items", tags=["Item Equivalents"])


class AddEquivalentRequest(BaseModel):
    """Request body for adding an equivalent part."""

    equivalent_item_id: str = Field(..., description="ID of the equivalent part")
    properties: Optional[Dict[str, Any]] = Field(
        None, description="Optional relationship properties"
    )


class AddEquivalentResponse(BaseModel):
    """Response for add equivalent operation."""

    ok: bool
    equivalent_id: str
    item_id: str
    equivalent_item_id: str
    properties: Optional[Dict[str, Any]] = None


class RemoveEquivalentResponse(BaseModel):
    """Response for remove equivalent operation."""

    ok: bool
    equivalent_id: str


class EquivalentEntry(BaseModel):
    """A single equivalent part entry."""

    id: str
    equivalent_item_id: Optional[str]
    equivalent_part: Optional[Dict[str, Any]] = None
    relationship: Dict[str, Any]


class EquivalentListResponse(BaseModel):
    """Response for listing equivalents."""

    item_id: str
    count: int
    equivalents: List[EquivalentEntry]


@equivalent_router.get(
    "/{item_id}/equivalents",
    response_model=EquivalentListResponse,
    summary="List equivalents for a Part",
)
async def list_equivalents(
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
        "Part Equivalent",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = EquivalentService(db, user_id=str(user.id), roles=user.roles)
    equivalents = service.list_equivalents(item_id)
    return EquivalentListResponse(
        item_id=item_id,
        count=len(equivalents),
        equivalents=equivalents,
    )


@equivalent_router.post(
    "/{item_id}/equivalents",
    response_model=AddEquivalentResponse,
    summary="Add an equivalent Part",
)
async def add_equivalent(
    item_id: str,
    request: AddEquivalentRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if item_id == request.equivalent_item_id:
        raise HTTPException(status_code=400, detail="Item cannot be equivalent to itself")

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    if item.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Invalid Part type")

    eq_item = db.get(Item, request.equivalent_item_id)
    if not eq_item:
        raise HTTPException(
            status_code=404,
            detail=f"Item {request.equivalent_item_id} not found",
        )
    if eq_item.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Invalid Part type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part Equivalent",
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

    service = EquivalentService(db, user_id=str(user.id), roles=user.roles)
    try:
        rel = service.add_equivalent(
            item_id=item_id,
            equivalent_item_id=request.equivalent_item_id,
            properties=request.properties,
            user_id=int(user.id),
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "Invalid Part" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return AddEquivalentResponse(
        ok=True,
        equivalent_id=rel.id,
        item_id=item_id,
        equivalent_item_id=request.equivalent_item_id,
        properties=request.properties,
    )


@equivalent_router.delete(
    "/{item_id}/equivalents/{equivalent_id}",
    response_model=RemoveEquivalentResponse,
    summary="Remove an equivalent relationship",
)
async def remove_equivalent(
    item_id: str,
    equivalent_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rel = db.get(Item, equivalent_id)
    if not rel or rel.item_type_id != "Part Equivalent":
        raise HTTPException(status_code=404, detail="Equivalent relationship not found")
    if rel.source_id != item_id and rel.related_id != item_id:
        raise HTTPException(status_code=404, detail="Equivalent relationship not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part Equivalent",
        AMLAction.delete,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = EquivalentService(db, user_id=str(user.id), roles=user.roles)
    try:
        service.remove_equivalent(equivalent_id, user_id=int(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RemoveEquivalentResponse(ok=True, equivalent_id=equivalent_id)
