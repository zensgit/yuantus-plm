from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService, CycleDetectedError
from yuantus.meta_engine.services.substitute_service import SubstituteService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.api.dependencies.auth import CurrentUser, get_current_user

bom_router = APIRouter(prefix="/bom", tags=["BOM"])


# ============================================================================
# Request/Response Models
# ============================================================================


class AddChildRequest(BaseModel):
    """Request body for adding a child to BOM."""

    child_id: str = Field(..., description="ID of the child item to add")
    quantity: float = Field(1.0, description="Quantity")
    uom: str = Field("EA", description="Unit of measure")
    find_num: Optional[str] = Field(None, description="Find number")
    refdes: Optional[str] = Field(None, description="Reference designator(s)")
    effectivity_from: Optional[datetime] = Field(None, description="Effectivity start date")
    effectivity_to: Optional[datetime] = Field(None, description="Effectivity end date")
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


@bom_router.get("/{item_id}/effective", response_model=Dict[str, Any])
async def get_effective_bom(
    item_id: str,
    date: Optional[datetime] = None,
    levels: int = Query(10, description="Explosion depth"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get BOM structure filtered by Effectivity Date.
    If date is not provided, defaults to Now (UTC).
    """
    if not date:
        date = datetime.utcnow()

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

    # Require read permission on the BOM relationship type as well.
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMService(db)
    try:
        return service.get_bom_structure(item_id, levels=levels, effective_date=date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@bom_router.get("/version/{version_id}", response_model=Dict[str, Any])
async def get_bom_by_version(
    version_id: str,
    levels: int = Query(10, description="Explosion depth"),
    db: Session = Depends(get_db),
):
    """
    Get BOM Snapshot defined by a specific ItemVersion.
    Resolves structure based on version's effectivity or creation time.
    """
    service = BOMService(db)
    try:
        return service.get_bom_for_version(version_id, levels=levels)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# S3.1: BOM Write APIs
# ============================================================================


@bom_router.get("/{parent_id}/tree", response_model=Dict[str, Any])
async def get_bom_tree(
    parent_id: str,
    depth: int = Query(10, description="Maximum depth to traverse (-1 for unlimited)"),
    effective_date: Optional[datetime] = Query(None, description="Effectivity filter date"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get BOM tree structure with specified depth.

    Args:
        parent_id: Root item ID
        depth: Maximum depth (-1 for unlimited, default 10)
        effective_date: Optional date for effectivity filtering

    Returns:
        Tree structure with children
    """
    root = db.get(Item, parent_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Item {parent_id} not found")

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

    service = BOMService(db)
    try:
        return service.get_tree(parent_id, depth=depth, effective_date=effective_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@bom_router.post(
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
    if not perm.check_permission(
        "Part BOM",
        AMLAction.add,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

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
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@bom_router.delete(
    "/{parent_id}/children/{child_id}",
    response_model=RemoveChildResponse,
)
async def remove_bom_child(
    parent_id: str,
    child_id: str,
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
    if not perm.check_permission(
        "Part BOM",
        AMLAction.delete,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        result = service.remove_child(parent_id=parent_id, child_id=child_id)
        db.commit()
        return result
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Where-Used API
# ============================================================================


class WhereUsedEntry(BaseModel):
    """A single where-used entry."""

    relationship: Dict[str, Any] = Field(..., description="BOM relationship item")
    parent: Dict[str, Any] = Field(..., description="Parent item that uses this item")
    level: int = Field(..., description="Level in the where-used hierarchy (1=direct)")


class WhereUsedResponse(BaseModel):
    """Response for where-used query."""

    item_id: str = Field(..., description="The queried item ID")
    count: int = Field(..., description="Number of parents found")
    parents: List[WhereUsedEntry] = Field(..., description="List of parent usages")


# ============================================================================
# BOM Compare API
# ============================================================================


class BOMCompareSummary(BaseModel):
    """Summary counts for BOM compare."""

    added: int
    removed: int
    changed: int


class BOMCompareEntry(BaseModel):
    """Entry for added/removed relationships."""

    parent_id: Optional[str] = None
    child_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    parent: Optional[Dict[str, Any]] = None
    child: Optional[Dict[str, Any]] = None


class BOMCompareChangedEntry(BaseModel):
    """Entry for changed relationships."""

    parent_id: Optional[str] = None
    child_id: Optional[str] = None
    before: Dict[str, Any] = Field(default_factory=dict)
    after: Dict[str, Any] = Field(default_factory=dict)
    parent: Optional[Dict[str, Any]] = None
    child: Optional[Dict[str, Any]] = None


class BOMCompareResponse(BaseModel):
    """Response for BOM compare."""

    summary: BOMCompareSummary
    added: List[BOMCompareEntry]
    removed: List[BOMCompareEntry]
    changed: List[BOMCompareChangedEntry]


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
                level=p["level"],
            )
            for p in parents
        ],
    )


@bom_router.get(
    "/compare",
    response_model=BOMCompareResponse,
    summary="Compare two BOM trees",
    description="Compare BOM structures between two items or versions.",
)
async def compare_bom(
    left_type: str = Query(..., description="item or version"),
    left_id: str = Query(..., description="Left item/version ID"),
    right_type: str = Query(..., description="item or version"),
    right_id: str = Query(..., description="Right item/version ID"),
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(False, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if max_levels < -1:
        raise HTTPException(status_code=400, detail="max_levels must be >= -1")

    left_type = left_type.strip().lower()
    right_type = right_type.strip().lower()
    if left_type not in {"item", "version"} or right_type not in {"item", "version"}:
        raise HTTPException(
            status_code=400,
            detail="left_type/right_type must be 'item' or 'version'",
        )

    def normalize_props(values: Optional[List[str]]) -> Optional[List[str]]:
        if not values:
            return None
        flattened: List[str] = []
        for raw in values:
            if raw is None:
                continue
            for part in str(raw).split(","):
                part = part.strip()
                if part:
                    flattened.append(part)
        return flattened or None

    include_props = normalize_props(include_relationship_props)

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMService(db)

    def resolve_tree(ref_type: str, ref_id: str) -> Dict[str, Any]:
        if ref_type == "item":
            item = db.get(Item, ref_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"Item {ref_id} not found")
            if not perm.check_permission(
                item.item_type_id,
                AMLAction.get,
                user_id=str(user.id),
                user_roles=user.roles,
            ):
                raise HTTPException(status_code=403, detail="Permission denied")
            return service.get_bom_structure(
                ref_id,
                levels=max_levels,
                effective_date=effective_at,
            )

        from yuantus.meta_engine.version.models import ItemVersion

        version = db.get(ItemVersion, ref_id)
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {ref_id} not found")
        item = db.get(Item, version.item_id)
        if not item:
            raise HTTPException(
                status_code=404, detail=f"Item {version.item_id} not found"
            )
        if not perm.check_permission(
            item.item_type_id,
            AMLAction.get,
            user_id=str(user.id),
            user_roles=user.roles,
        ):
            raise HTTPException(status_code=403, detail="Permission denied")

        if effective_at:
            return service.get_bom_structure(
                item.id,
                levels=max_levels,
                effective_date=effective_at,
            )
        try:
            return service.get_bom_for_version(ref_id, levels=max_levels)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    def normalize_root(tree: Dict[str, Any]) -> Dict[str, Any]:
        if not tree:
            return tree
        normalized = dict(tree)
        normalized["config_id"] = "ROOT"
        return normalized

    left_tree = normalize_root(resolve_tree(left_type, left_id))
    right_tree = normalize_root(resolve_tree(right_type, right_id))

    return service.compare_bom_trees(
        left_tree,
        right_tree,
        include_relationship_props=include_props,
        include_child_fields=include_child_fields,
    )


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

    service = SubstituteService(db, user_id=str(user.id), roles=user.roles)
    try:
        sub_rel = service.add_substitute(
            bom_line_id=bom_line_id,
            substitute_item_id=request.substitute_item_id,
            properties=request.properties,
            user_id=int(user.id),
        )
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

    service = SubstituteService(db, user_id=str(user.id), roles=user.roles)
    try:
        service.remove_substitute(substitute_id, user_id=int(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RemoveSubstituteResponse(ok=True, substitute_id=substitute_id)
