from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.suspended_guard import SuspendedStateError
from yuantus.meta_engine.services.substitute_service import SubstituteService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.api.dependencies.auth import CurrentUser, get_current_user

bom_router = APIRouter(prefix="/bom", tags=["BOM"])


# ============================================================================
# Request/Response Models
# ============================================================================


# ============================================================================
# Where-Used API
# ============================================================================


class WhereUsedEntry(BaseModel):
    """A single where-used entry."""

    relationship: Dict[str, Any] = Field(..., description="BOM relationship item")
    parent: Dict[str, Any] = Field(..., description="Parent item that uses this item")
    child: Optional[Dict[str, Any]] = Field(
        None, description="Child item (the queried item)"
    )
    parent_number: Optional[str] = Field(
        None, description="Alias parent item_number for UI"
    )
    parent_name: Optional[str] = Field(None, description="Alias parent name for UI")
    child_number: Optional[str] = Field(
        None, description="Alias child item_number for UI"
    )
    child_name: Optional[str] = Field(None, description="Alias child name for UI")
    line: Dict[str, Any] = Field(
        default_factory=dict, description="Standardized BOM line fields"
    )
    line_normalized: Dict[str, Any] = Field(
        default_factory=dict, description="Normalized BOM line fields"
    )
    level: int = Field(..., description="Level in the where-used hierarchy (1=direct)")


class WhereUsedResponse(BaseModel):
    """Response for where-used query."""

    item_id: str = Field(..., description="The queried item ID")
    count: int = Field(..., description="Number of parents found")
    parents: List[WhereUsedEntry] = Field(..., description="List of parent usages")
    recursive: bool = Field(
        False, description="Whether recursive search was enabled"
    )
    max_levels: int = Field(10, description="Maximum recursion depth applied")


class WhereUsedLineFieldSpec(BaseModel):
    """Field metadata for where-used BOM line output."""

    field: str
    severity: str
    normalized: str
    description: str


class WhereUsedSchemaResponse(BaseModel):
    """Schema metadata for where-used line fields."""

    line_fields: List[WhereUsedLineFieldSpec]


# ============================================================================
# BOM Compare API DTOs — moved to bom_compare_router.py (R1 decomposition)
# ============================================================================


class AddSubstituteRequest(BaseModel):
    """Request body for adding a substitute to a BOM line."""

    substitute_item_id: str = Field(..., description="ID of the substitute item")
    properties: Optional[Dict[str, Any]] = Field(
        None, description="Optional relationship properties (rank, note, etc.)"
    )


class AddSubstituteResponse(BaseModel):
    """Response for add substitute operation."""

    ok: bool
    substitute_id: str
    bom_line_id: str
    substitute_item_id: str


class RemoveSubstituteResponse(BaseModel):
    """Response for remove substitute operation."""

    ok: bool
    substitute_id: str


class SubstituteEntry(BaseModel):
    """A substitute entry for a BOM line."""

    id: str
    relationship: Dict[str, Any] = Field(default_factory=dict)
    part: Optional[Dict[str, Any]] = None
    substitute_part: Optional[Dict[str, Any]] = None
    rank: Optional[Any] = None
    substitute_number: Optional[str] = None
    substitute_name: Optional[str] = None


class SubstituteListResponse(BaseModel):
    """Response for listing substitutes for a BOM line."""

    bom_line_id: str
    count: int
    substitutes: List[SubstituteEntry]


@bom_router.get(
    "/{item_id}/where-used",
    response_model=WhereUsedResponse,
    summary="Find where an item is used",
    description="Returns all parent items that use this item in their BOM. "
    "Supports recursive search to find all ancestors up to max_levels.",
)
async def get_where_used(
    item_id: str,
    recursive: bool = Query(False, description="Include parent's parents recursively"),
    max_levels: int = Query(10, description="Maximum levels to traverse (only with recursive=true)"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Find all parent items that use this item in their BOM.

    Use Cases:
    - Impact analysis: "Which assemblies will be affected if I change this part?"
    - Compliance: "Where is this component used across products?"
    - Cost rollup: "What assemblies include this part?"

    Args:
        item_id: The child item ID to search for
        recursive: If true, also finds grandparents, great-grandparents, etc.
        max_levels: Maximum depth for recursive search (default 10)

    Returns:
        WhereUsedResponse with list of parent usages
    """
    # Check item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # Check permission on the item type
    perm = MetaPermissionService(db)
    if not perm.check_permission(
        item.item_type_id,
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Check permission on BOM relationship type
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMService(db)
    parents = service.get_where_used(
        item_id=item_id,
        recursive=recursive,
        max_levels=max_levels,
    )

    return WhereUsedResponse(
        item_id=item_id,
        count=len(parents),
        parents=[
            WhereUsedEntry(
                relationship=p["relationship"],
                parent=p["parent"],
                child=p.get("child"),
                parent_number=p.get("parent_number"),
                parent_name=p.get("parent_name"),
                child_number=p.get("child_number"),
                child_name=p.get("child_name"),
                line=p.get("line") or {},
                line_normalized=p.get("line_normalized") or {},
                level=p["level"],
            )
            for p in parents
        ],
        recursive=recursive,
        max_levels=max_levels,
    )


@bom_router.get(
    "/where-used/schema",
    response_model=WhereUsedSchemaResponse,
    summary="Get where-used line schema",
    description="Returns line field mapping and normalization metadata for where-used UI.",
)
async def get_where_used_schema(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    return WhereUsedSchemaResponse(line_fields=BOMService.line_schema())


@bom_router.get(
    "/{bom_line_id}/substitutes",
    response_model=SubstituteListResponse,
    summary="List substitutes for a BOM line",
)
async def list_bom_substitutes(
    bom_line_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bom_line = db.get(Item, bom_line_id)
    if not bom_line:
        raise HTTPException(status_code=404, detail=f"BOM line {bom_line_id} not found")
    if bom_line.item_type_id not in {"Part BOM", "Manufacturing BOM"}:
        raise HTTPException(status_code=400, detail="Invalid BOM line type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = SubstituteService(db, user_id=str(user.id), roles=user.roles)
    substitutes = service.get_bom_substitutes(bom_line_id)

    return SubstituteListResponse(
        bom_line_id=bom_line_id,
        count=len(substitutes),
        substitutes=substitutes,
    )


@bom_router.post(
    "/{bom_line_id}/substitutes",
    response_model=AddSubstituteResponse,
    summary="Add a substitute to a BOM line",
)
async def add_bom_substitute(
    bom_line_id: str,
    request: AddSubstituteRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bom_line = db.get(Item, bom_line_id)
    if not bom_line:
        raise HTTPException(status_code=404, detail=f"BOM line {bom_line_id} not found")
    if bom_line.item_type_id not in {"Part BOM", "Manufacturing BOM"}:
        raise HTTPException(status_code=400, detail="Invalid BOM line type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM Substitute",
        AMLAction.add,
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

    if bom_line.source_id:
        parent = db.get(Item, bom_line.source_id)
        if parent:
            parent_type = db.get(ItemType, parent.item_type_id)
            locked, locked_state = is_item_locked(db, parent, parent_type)
            if locked:
                raise HTTPException(
                    status_code=409,
                    detail=f"Item is locked in state '{locked_state or parent.state}'",
                )

    service = SubstituteService(db, user_id=str(user.id), roles=user.roles)
    try:
        sub_rel = service.add_substitute(
            bom_line_id=bom_line_id,
            substitute_item_id=request.substitute_item_id,
            properties=request.properties,
            user_id=int(user.id),
        )
    except NotLatestReleasedError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.to_detail())
    except SuspendedStateError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.to_detail())
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "Invalid BOM Line" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return AddSubstituteResponse(
        ok=True,
        substitute_id=sub_rel.id,
        bom_line_id=bom_line_id,
        substitute_item_id=request.substitute_item_id,
    )


@bom_router.delete(
    "/{bom_line_id}/substitutes/{substitute_id}",
    response_model=RemoveSubstituteResponse,
    summary="Remove a substitute from a BOM line",
)
async def remove_bom_substitute(
    bom_line_id: str,
    substitute_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bom_line = db.get(Item, bom_line_id)
    if not bom_line:
        raise HTTPException(status_code=404, detail=f"BOM line {bom_line_id} not found")
    if bom_line.item_type_id not in {"Part BOM", "Manufacturing BOM"}:
        raise HTTPException(status_code=400, detail="Invalid BOM line type")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM Substitute",
        AMLAction.delete,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    if bom_line.source_id:
        parent = db.get(Item, bom_line.source_id)
        if parent:
            parent_type = db.get(ItemType, parent.item_type_id)
            locked, locked_state = is_item_locked(db, parent, parent_type)
            if locked:
                raise HTTPException(
                    status_code=409,
                    detail=f"Item is locked in state '{locked_state or parent.state}'",
                )

    service = SubstituteService(db, user_id=str(user.id), roles=user.roles)
    try:
        service.remove_substitute(substitute_id, user_id=int(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RemoveSubstituteResponse(ok=True, substitute_id=substitute_id)
