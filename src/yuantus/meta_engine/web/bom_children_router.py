from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService, CycleDetectedError
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.services.suspended_guard import SuspendedStateError

bom_children_router = APIRouter(prefix="/bom", tags=["BOM"])


class AddChildRequest(BaseModel):
    """Request body for adding a child to BOM."""

    child_id: str = Field(..., description="ID of the child item to add")
    quantity: float = Field(1.0, description="Quantity")
    uom: str = Field("EA", description="Unit of measure")
    find_num: Optional[str] = Field(None, description="Find number")
    refdes: Optional[str] = Field(None, description="Reference designator(s)")
    effectivity_from: Optional[datetime] = Field(None, description="Effectivity start date")
    effectivity_to: Optional[datetime] = Field(None, description="Effectivity end date")
    config_condition: Optional[Any] = Field(
        None, description="Configuration condition (JSON or simple 'key=value' string)"
    )
    extra_properties: Optional[Dict[str, Any]] = Field(
        None, description="Additional properties"
    )


class AddChildResponse(BaseModel):
    """Response for add child operation."""

    ok: bool
    relationship_id: str
    parent_id: str
    child_id: str
    effectivity_id: Optional[str] = Field(None, description="Effectivity record ID if dates were provided")


class RemoveChildResponse(BaseModel):
    """Response for remove child operation."""

    ok: bool
    relationship_id: str


class CycleErrorResponse(BaseModel):
    """Response when cycle is detected."""

    error: str = "CYCLE_DETECTED"
    message: str
    parent_id: str
    child_id: str
    cycle_path: List[str]


@bom_children_router.post(
    "/{parent_id}/children",
    response_model=AddChildResponse,
    responses={
        409: {
            "model": CycleErrorResponse,
            "description": "Cycle detected in BOM structure",
        }
    },
)
async def add_bom_child(
    parent_id: str,
    request: AddChildRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a child item to a parent BOM.

    Returns 409 Conflict with cycle path if adding would create a cycle.

    Args:
        parent_id: Parent item ID
        request: Child details (child_id, quantity, uom, find_num, refdes, etc.)

    Returns:
        AddChildResponse with relationship_id on success
        CycleErrorResponse (409) if cycle detected
    """
    service = BOMService(db)
    perm = MetaPermissionService(db)
    parent = db.get(Item, parent_id)
    if not parent:
        raise HTTPException(status_code=404, detail=f"Item {parent_id} not found")
    if not perm.check_permission(
        "Part BOM",
        AMLAction.add,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    parent_type = db.get(ItemType, parent.item_type_id)
    locked, locked_state = is_item_locked(db, parent, parent_type)
    if locked:
        raise HTTPException(
            status_code=409,
            detail=f"Item is locked in state '{locked_state or parent.state}'",
        )

    try:
        result = service.add_child(
            parent_id=parent_id,
            child_id=request.child_id,
            user_id=user.id,
            quantity=request.quantity,
            uom=request.uom,
            find_num=request.find_num,
            refdes=request.refdes,
            effectivity_from=request.effectivity_from,
            effectivity_to=request.effectivity_to,
            config_condition=request.config_condition,
            extra_properties=request.extra_properties,
        )
        db.commit()
        return result
    except CycleDetectedError as e:
        db.rollback()
        return JSONResponse(
            status_code=409,
            content=e.to_dict(),
        )
    except NotLatestReleasedError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.to_detail())
    except SuspendedStateError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.to_detail())
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@bom_children_router.delete(
    "/{parent_id}/children/{child_id}",
    response_model=RemoveChildResponse,
)
async def remove_bom_child(
    parent_id: str,
    child_id: str,
    uom: Optional[str] = Query(
        None,
        description="Optional UOM discriminator when multiple parent/child BOM lines exist",
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a child from a parent BOM.

    Args:
        parent_id: Parent item ID
        child_id: Child item ID to remove

    Returns:
        RemoveChildResponse with relationship_id on success
    """
    service = BOMService(db)
    perm = MetaPermissionService(db)
    parent = db.get(Item, parent_id)
    if not parent:
        raise HTTPException(status_code=404, detail=f"Item {parent_id} not found")
    if not perm.check_permission(
        "Part BOM",
        AMLAction.delete,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    parent_type = db.get(ItemType, parent.item_type_id)
    locked, locked_state = is_item_locked(db, parent, parent_type)
    if locked:
        raise HTTPException(
            status_code=409,
            detail=f"Item is locked in state '{locked_state or parent.state}'",
        )

    try:
        result = service.remove_child(parent_id=parent_id, child_id=child_id, uom=uom)
        db.commit()
        return result
    except ValueError as e:
        db.rollback()
        status_code = 400 if "multiple bom relationships" in str(e).lower() else 404
        raise HTTPException(status_code=status_code, detail=str(e)) from e
