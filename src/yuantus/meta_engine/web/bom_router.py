from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import json
import io
import threading
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService, CycleDetectedError
from yuantus.meta_engine.services.bom_conversion_service import BOMConversionService
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.bom_obsolete_service import BOMObsoleteService
from yuantus.meta_engine.services.bom_rollup_service import BOMRollupService
from yuantus.meta_engine.services.substitute_service import SubstituteService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.api.dependencies.auth import CurrentUser, get_current_user

bom_router = APIRouter(prefix="/bom", tags=["BOM"])


# ============================================================================
# Request/Response Models
# ============================================================================


def _parse_config_selection(config: Optional[str]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    try:
        payload = json.loads(config)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid config JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Config must be a JSON object")
    return payload


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


class ConvertBomRequest(BaseModel):
    """Request body for EBOM -> MBOM conversion."""

    root_id: str = Field(..., description="Root EBOM Part ID")


class ConvertBomResponse(BaseModel):
    """Response for EBOM -> MBOM conversion."""

    ok: bool
    source_root_id: str
    mbom_root_id: str
    mbom_root_type: str
    mbom_root_config_id: str


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


@bom_router.get("/{item_id}/effective", response_model=Dict[str, Any])
async def get_effective_bom(
    item_id: str,
    date: Optional[datetime] = None,
    levels: int = Query(10, description="Explosion depth"),
    lot_number: Optional[str] = Query(None, description="Lot number for effectivity"),
    serial_number: Optional[str] = Query(None, description="Serial number for effectivity"),
    unit_position: Optional[str] = Query(None, description="Unit position for effectivity"),
    config: Optional[str] = Query(None, description="Configuration selection JSON"),
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
    config_selection = _parse_config_selection(config)
    try:
        return service.get_bom_structure(
            item_id,
            levels=levels,
            effective_date=date,
            config_selection=config_selection,
            lot_number=lot_number,
            serial_number=serial_number,
            unit_position=unit_position,
        )
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
# MBOM Conversion
# ============================================================================


@bom_router.post(
    "/convert/ebom-to-mbom",
    response_model=ConvertBomResponse,
    summary="Convert EBOM to MBOM",
)
async def convert_ebom_to_mbom(
    request: ConvertBomRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Convert an Engineering BOM (EBOM) to a Manufacturing BOM (MBOM).
    """
    root = db.get(Item, request.root_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Item {request.root_id} not found")
    if root.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Only Part EBOM can be converted")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        "Part BOM",
        AMLAction.add,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMConversionService(db)
    try:
        mbom_root = service.convert_ebom_to_mbom(request.root_id, user_id=int(user.id))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return ConvertBomResponse(
        ok=True,
        source_root_id=request.root_id,
        mbom_root_id=mbom_root.id,
        mbom_root_type=mbom_root.item_type_id,
        mbom_root_config_id=mbom_root.config_id,
    )


# ============================================================================
# S3.1: BOM Write APIs
# ============================================================================


@bom_router.get("/{parent_id}/tree", response_model=Dict[str, Any])
async def get_bom_tree(
    parent_id: str,
    depth: int = Query(10, description="Maximum depth to traverse (-1 for unlimited)"),
    effective_date: Optional[datetime] = Query(None, description="Effectivity filter date"),
    lot_number: Optional[str] = Query(None, description="Lot number for effectivity"),
    serial_number: Optional[str] = Query(None, description="Serial number for effectivity"),
    unit_position: Optional[str] = Query(None, description="Unit position for effectivity"),
    config: Optional[str] = Query(None, description="Configuration selection JSON"),
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
    config_selection = _parse_config_selection(config)
    try:
        return service.get_tree(
            parent_id,
            depth=depth,
            effective_date=effective_date,
            config_selection=config_selection,
            lot_number=lot_number,
            serial_number=serial_number,
            unit_position=unit_position,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@bom_router.get("/mbom/{parent_id}/tree", response_model=Dict[str, Any])
async def get_mbom_tree(
    parent_id: str,
    depth: int = Query(10, description="Maximum depth to traverse (-1 for unlimited)"),
    config: Optional[str] = Query(None, description="Configuration selection JSON"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get MBOM tree structure with specified depth.
    """
    root = db.get(Item, parent_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Item {parent_id} not found")
    if root.item_type_id != "Manufacturing Part":
        raise HTTPException(status_code=400, detail="Invalid Manufacturing Part ID")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Manufacturing Part",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        "Manufacturing BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMService(db)
    config_selection = _parse_config_selection(config)
    try:
        return service.get_tree(
            parent_id,
            depth=depth,
            relationship_types=["Manufacturing BOM"],
            config_selection=config_selection,
        )
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
        result = service.remove_child(parent_id=parent_id, child_id=child_id)
        db.commit()
        return result
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# BOM Obsolete Handling + Weight Rollup
# ============================================================================


@bom_router.get("/{item_id}/obsolete", response_model=ObsoleteScanResponse)
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


@bom_router.post("/{item_id}/obsolete/resolve", response_model=ObsoleteResolveResponse)
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
        raise HTTPException(status_code=400, detail=str(e))


@bom_router.post("/{item_id}/rollup/weight", response_model=Dict[str, Any])
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
# BOM Compare API
# ============================================================================


class BOMCompareSummary(BaseModel):
    """Summary counts for BOM compare."""

    added: int
    removed: int
    changed: int
    changed_major: int = 0
    changed_minor: int = 0
    changed_info: int = 0


class BOMCompareEntry(BaseModel):
    """Entry for added/removed relationships."""

    parent_id: Optional[str] = None
    child_id: Optional[str] = None
    relationship_id: Optional[str] = None
    line_key: Optional[str] = None
    parent_config_id: Optional[str] = None
    child_config_id: Optional[str] = None
    level: Optional[int] = None
    path: Optional[List[Dict[str, Any]]] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    line: Dict[str, Any] = Field(default_factory=dict, description="Standardized BOM line fields")
    line_normalized: Dict[str, Any] = Field(
        default_factory=dict, description="Normalized line fields for comparisons"
    )
    parent: Optional[Dict[str, Any]] = None
    child: Optional[Dict[str, Any]] = None
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    child_number: Optional[str] = None
    child_name: Optional[str] = None


class BOMCompareFieldDiff(BaseModel):
    """Field-level diff for changed BOM line properties."""

    field: str
    left: Any = None
    right: Any = None
    normalized_left: Any = None
    normalized_right: Any = None
    severity: str = "info"


class BOMCompareChangedEntry(BaseModel):
    """Entry for changed relationships."""

    parent_id: Optional[str] = None
    child_id: Optional[str] = None
    relationship_id: Optional[str] = None
    line_key: Optional[str] = None
    parent_config_id: Optional[str] = None
    child_config_id: Optional[str] = None
    level: Optional[int] = None
    path: Optional[List[Dict[str, Any]]] = None
    before: Dict[str, Any] = Field(default_factory=dict)
    after: Dict[str, Any] = Field(default_factory=dict)
    before_line: Dict[str, Any] = Field(default_factory=dict)
    after_line: Dict[str, Any] = Field(default_factory=dict)
    before_normalized: Dict[str, Any] = Field(default_factory=dict)
    after_normalized: Dict[str, Any] = Field(default_factory=dict)
    changes: List[BOMCompareFieldDiff] = Field(default_factory=list)
    severity: Optional[str] = None
    parent: Optional[Dict[str, Any]] = None
    child: Optional[Dict[str, Any]] = None
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    child_number: Optional[str] = None
    child_name: Optional[str] = None


class BOMCompareResponse(BaseModel):
    """Response for BOM compare."""

    summary: BOMCompareSummary
    added: List[BOMCompareEntry]
    removed: List[BOMCompareEntry]
    changed: List[BOMCompareChangedEntry]


class BOMCompareFieldSpec(BaseModel):
    """Field metadata for BOM compare diff."""

    field: str
    severity: str
    normalized: str
    description: str


class BOMCompareModeSpec(BaseModel):
    """Compare mode specification."""

    mode: str
    line_key: Optional[str] = None
    include_relationship_props: List[str] = Field(default_factory=list)
    aggregate_quantities: bool = False
    aliases: List[str] = Field(default_factory=list)
    description: str


class BOMCompareSchemaResponse(BaseModel):
    """Schema metadata for BOM compare."""

    line_fields: List[BOMCompareFieldSpec]
    compare_modes: List[BOMCompareModeSpec]
    line_key_options: List[str]
    defaults: Dict[str, Any]


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
    "/compare/schema",
    response_model=BOMCompareSchemaResponse,
    summary="Get BOM compare schema",
    description="Returns field-level mapping, severity, and compare mode options.",
)
async def get_bom_compare_schema(
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

    return BOMService.compare_schema()


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
    line_key: str = Query(
        "child_config",
        description=(
            "Line key strategy: child_config, child_id, relationship_id, "
            "child_config_find_num, child_config_refdes, child_config_find_refdes, "
            "child_id_find_num, child_id_refdes, child_id_find_refdes, "
            "child_config_find_num_qty, child_id_find_num_qty, line_full"
        ),
    ),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    include_substitutes: bool = Query(False, description="Include substitutes in compare"),
    include_effectivity: bool = Query(False, description="Include effectivity records in compare"),
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

    aggregate_quantities = False

    try:
        mode_line_key, mode_props, mode_aggregate = BOMService.resolve_compare_mode(
            compare_mode
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if mode_line_key:
        line_key = mode_line_key
        include_props = mode_props
        aggregate_quantities = mode_aggregate
    else:
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
                include_substitutes=include_substitutes,
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
                include_substitutes=include_substitutes,
            )
        try:
            return service.get_bom_for_version(
                ref_id,
                levels=max_levels,
                include_substitutes=include_substitutes,
            )
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
        line_key=line_key,
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        aggregate_quantities=aggregate_quantities,
    )


@bom_router.get(
    "/compare/delta/preview",
    summary="Preview BOM delta patch",
    description="Generate read-only delta operations from BOM compare result.",
)
async def compare_bom_delta_preview(
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
    line_key: str = Query("child_config", description="Line key strategy"),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    fields: Optional[List[str]] = Query(
        None,
        description=(
            "Optional exported fields: op,line_key,parent_id,child_id,relationship_id,"
            "severity,risk_level,change_count,field,before,after,properties"
        ),
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    compare_result = await compare_bom(
        left_type=left_type,
        left_id=left_id,
        right_type=right_type,
        right_id=right_id,
        max_levels=max_levels,
        effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key,
        compare_mode=compare_mode,
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user,
        db=db,
    )
    service = BOMService(db)
    delta = service.build_delta_preview(compare_result)
    delta["compare_summary"] = compare_result.get("summary") or {}
    try:
        return service.filter_delta_preview_fields(delta, fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@bom_router.get(
    "/compare/delta/export",
    summary="Export BOM delta patch",
    description="Export delta preview as json, csv or md.",
)
async def compare_bom_delta_export(
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
    line_key: str = Query("child_config", description="Line key strategy"),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    fields: Optional[List[str]] = Query(
        None,
        description=(
            "Optional exported fields: op,line_key,parent_id,child_id,relationship_id,"
            "severity,risk_level,change_count,field,before,after,properties"
        ),
    ),
    export_format: str = Query("json", description="json|csv|md"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    compare_result = await compare_bom(
        left_type=left_type,
        left_id=left_id,
        right_type=right_type,
        right_id=right_id,
        max_levels=max_levels,
        effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key,
        compare_mode=compare_mode,
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user,
        db=db,
    )
    service = BOMService(db)
    delta = service.build_delta_preview(compare_result)
    delta["compare_summary"] = compare_result.get("summary") or {}
    try:
        delta_filtered = service.filter_delta_preview_fields(delta, fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized = (export_format or "json").strip().lower()
    if normalized == "json":
        payload = json.dumps(delta_filtered, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(payload),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="bom-delta-preview.json"'},
        )
    if normalized == "csv":
        csv_text = service.export_delta_csv(delta, fields=fields)
        return StreamingResponse(
            io.BytesIO(csv_text.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="bom-delta-preview.csv"'},
        )
    if normalized == "md":
        md_text = service.export_delta_markdown(delta_filtered, fields=fields)
        return StreamingResponse(
            io.BytesIO(md_text.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="bom-delta-preview.md"'},
        )
    raise HTTPException(status_code=400, detail="export_format must be json, csv or md")


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


# ============================================================================
# BOM Compare Summarized – Module-level snapshot store
# ============================================================================

_BOM_COMPARE_SUMMARIZED_SNAPSHOTS: List[Dict[str, Any]] = []
_BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK = threading.Lock()


# ============================================================================
# Helpers: transform compare result → summarized rows
# ============================================================================


def _compare_result_to_summarized_rows(result: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a raw compare result into a flat row list with quantity deltas."""
    rows: List[Dict[str, Any]] = []
    quantity_delta_total = 0.0

    for item in result.get("added", []):
        props = item.get("properties") or {}
        qty = props.get("quantity")
        qty_f = float(qty) if qty is not None else 0.0
        rows.append({
            "line_key": item.get("line_key"),
            "parent_id": item.get("parent_id"),
            "child_id": item.get("child_id"),
            "status": "added",
            "quantity_before": None,
            "quantity_after": qty_f if qty is not None else None,
            "quantity_delta": qty_f,
            "uom_before": None,
            "uom_after": props.get("uom"),
            "relationship_id_before": None,
            "relationship_id_after": item.get("relationship_id"),
            "severity": None,
            "change_fields": [],
        })
        quantity_delta_total += qty_f

    for item in result.get("removed", []):
        props = item.get("properties") or {}
        qty = props.get("quantity")
        qty_f = float(qty) if qty is not None else 0.0
        rows.append({
            "line_key": item.get("line_key"),
            "parent_id": item.get("parent_id"),
            "child_id": item.get("child_id"),
            "status": "removed",
            "quantity_before": qty_f if qty is not None else None,
            "quantity_after": None,
            "quantity_delta": -qty_f,
            "uom_before": props.get("uom"),
            "uom_after": None,
            "relationship_id_before": item.get("relationship_id"),
            "relationship_id_after": None,
            "severity": None,
            "change_fields": [],
        })
        quantity_delta_total += -qty_f

    for item in result.get("changed", []):
        before = item.get("before") or {}
        after = item.get("after") or {}
        qty_before = before.get("quantity")
        qty_after = after.get("quantity")
        qty_b = float(qty_before) if qty_before is not None else 0.0
        qty_a = float(qty_after) if qty_after is not None else 0.0
        change_fields = [c.get("field") for c in (item.get("changes") or []) if c.get("field")]
        rows.append({
            "line_key": item.get("line_key"),
            "parent_id": item.get("parent_id"),
            "child_id": item.get("child_id"),
            "status": "changed",
            "quantity_before": qty_b if qty_before is not None else None,
            "quantity_after": qty_a if qty_after is not None else None,
            "quantity_delta": qty_a - qty_b,
            "uom_before": before.get("uom"),
            "uom_after": after.get("uom"),
            "relationship_id_before": item.get("relationship_id"),
            "relationship_id_after": item.get("relationship_id"),
            "severity": item.get("severity"),
            "change_fields": change_fields,
        })
        quantity_delta_total += qty_a - qty_b

    summary = dict(result.get("summary", {}))
    summary["total"] = len(rows)
    summary["total_rows"] = len(rows)
    summary["quantity_delta_total"] = quantity_delta_total

    return {"summary": summary, "rows": rows}


_SUMMARIZED_CSV_HEADERS = (
    "line_key,parent_id,child_id,status,quantity_before,quantity_after,"
    "quantity_delta,uom_before,uom_after,relationship_id_before,relationship_id_after,"
    "severity,change_fields"
)

_SUMMARIZED_MD_HEADERS = (
    "| line_key | parent_id | child_id | status | quantity_before | quantity_after | "
    "quantity_delta | uom_before | uom_after | relationship_id_before | "
    "relationship_id_after | severity | change_fields |"
)


def _rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    lines = [_SUMMARIZED_CSV_HEADERS]
    for r in rows:
        def _v(val):
            if val is None:
                return ""
            if isinstance(val, list):
                return ";".join(str(x) for x in val)
            if isinstance(val, float):
                return str(val)
            return str(val)

        lines.append(",".join([
            _v(r.get("line_key")), _v(r.get("parent_id")), _v(r.get("child_id")),
            _v(r.get("status")), _v(r.get("quantity_before")), _v(r.get("quantity_after")),
            _v(r.get("quantity_delta")), _v(r.get("uom_before")), _v(r.get("uom_after")),
            _v(r.get("relationship_id_before")), _v(r.get("relationship_id_after")),
            _v(r.get("severity")), _v(r.get("change_fields")),
        ]))
    return "\n".join(lines)


def _rows_to_markdown(rows: List[Dict[str, Any]], title: str = "BOM Compare Summarized") -> str:
    sep = "| " + " | ".join(["---"] * 13) + " |"
    lines = [f"# {title}", "", _SUMMARIZED_MD_HEADERS, sep]
    for r in rows:
        def _v(val):
            if val is None:
                return ""
            if isinstance(val, list):
                return ";".join(str(x) for x in val)
            return str(val)

        lines.append("| " + " | ".join([
            _v(r.get("line_key")), _v(r.get("parent_id")), _v(r.get("child_id")),
            _v(r.get("status")), _v(r.get("quantity_before")), _v(r.get("quantity_after")),
            _v(r.get("quantity_delta")), _v(r.get("uom_before")), _v(r.get("uom_after")),
            _v(r.get("relationship_id_before")), _v(r.get("relationship_id_after")),
            _v(r.get("severity")), _v(r.get("change_fields")),
        ]) + " |")
    return "\n".join(lines)


def _validate_export_format(fmt: str) -> None:
    if fmt not in {"json", "csv", "md"}:
        raise HTTPException(status_code=400, detail="export_format must be json, csv or md")


def _find_snapshot(snapshot_id: str) -> Dict[str, Any]:
    with _BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        for s in _BOM_COMPARE_SUMMARIZED_SNAPSHOTS:
            if s["snapshot_id"] == snapshot_id:
                return s
    raise HTTPException(status_code=404, detail=f"snapshot {snapshot_id} not found")


# ============================================================================
# Snapshot diff helpers
# ============================================================================


def _diff_snapshot_rows(
    left_rows: List[Dict[str, Any]],
    right_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare two lists of summarized rows and return differences."""
    left_by_key = {r["line_key"]: r for r in left_rows}
    right_by_key = {r["line_key"]: r for r in right_rows}
    all_keys = list(dict.fromkeys(list(left_by_key.keys()) + list(right_by_key.keys())))

    differences: List[Dict[str, Any]] = []
    added = 0
    removed = 0
    changed = 0

    compare_fields = [
        "quantity_before", "quantity_after", "quantity_delta",
        "uom_before", "uom_after", "status", "severity",
        "relationship_id_before", "relationship_id_after",
    ]

    for key in all_keys:
        left_row = left_by_key.get(key)
        right_row = right_by_key.get(key)
        if left_row and not right_row:
            removed += 1
            differences.append({
                "change_type": "removed",
                "row_key": key,
                "line_key": key,
                "parent_id": left_row.get("parent_id"),
                "child_id": left_row.get("child_id"),
                "status": left_row.get("status"),
                "changed_fields": [],
            })
        elif right_row and not left_row:
            added += 1
            differences.append({
                "change_type": "added",
                "row_key": key,
                "line_key": key,
                "parent_id": right_row.get("parent_id"),
                "child_id": right_row.get("child_id"),
                "status": right_row.get("status"),
                "changed_fields": [],
            })
        else:
            changed_fields = [
                f for f in compare_fields if left_row.get(f) != right_row.get(f)
            ]
            if changed_fields:
                changed += 1
                differences.append({
                    "change_type": "changed",
                    "row_key": key,
                    "line_key": key,
                    "parent_id": right_row.get("parent_id"),
                    "child_id": right_row.get("child_id"),
                    "status": right_row.get("status"),
                    "changed_fields": changed_fields,
                })

    return {
        "summary": {
            "total_differences": len(differences),
            "added": added,
            "removed": removed,
            "changed": changed,
            "left_rows": len(left_rows),
            "right_rows": len(right_rows),
        },
        "differences": differences,
    }


_DIFF_CSV_HEADERS = "change_type,row_key,line_key,parent_id,child_id,status,changed_fields"


def _diff_to_csv(diff_result: Dict[str, Any]) -> str:
    lines = [_DIFF_CSV_HEADERS]
    for d in diff_result.get("differences", []):
        cf = ";".join(d.get("changed_fields", []))
        lines.append(",".join([
            str(d.get("change_type", "")),
            str(d.get("row_key", "")),
            str(d.get("line_key", "")),
            str(d.get("parent_id", "")),
            str(d.get("child_id", "")),
            str(d.get("status", "")),
            cf,
        ]))
    return "\n".join(lines)


def _diff_to_markdown(diff_result: Dict[str, Any], title: str) -> str:
    sep = "| " + " | ".join(["---"] * 7) + " |"
    header = "| change_type | row_key | line_key | parent_id | child_id | status | changed_fields |"
    lines = [f"# {title}", "", header, sep]
    for d in diff_result.get("differences", []):
        cf = ";".join(d.get("changed_fields", []))
        lines.append("| " + " | ".join([
            str(d.get("change_type", "")),
            str(d.get("row_key", "")),
            str(d.get("line_key", "")),
            str(d.get("parent_id", "")),
            str(d.get("child_id", "")),
            str(d.get("status", "")),
            cf,
        ]) + " |")
    return "\n".join(lines)


def _export_diff(diff_result: Dict[str, Any], export_format: str, filename_base: str):
    _validate_export_format(export_format)
    if export_format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(diff_result, indent=2, default=str).encode()),
            media_type="application/json",
            headers={"content-disposition": f'attachment; filename="{filename_base}.json"'},
        )
    if export_format == "csv":
        return StreamingResponse(
            io.BytesIO(_diff_to_csv(diff_result).encode()),
            media_type="text/csv",
            headers={"content-disposition": f'attachment; filename="{filename_base}.csv"'},
        )
    md = _diff_to_markdown(diff_result, "BOM Summarized Snapshot Diff")
    return StreamingResponse(
        io.BytesIO(md.encode()),
        media_type="text/markdown",
        headers={"content-disposition": f'attachment; filename="{filename_base}.md"'},
    )


# ============================================================================
# BOM Compare Summarized Endpoints
# ============================================================================


class SnapshotCreateRequest(BaseModel):
    left_type: str = "item"
    left_id: str
    right_type: str = "item"
    right_id: str
    max_levels: int = 10
    effective_at: Optional[datetime] = None
    include_child_fields: bool = False
    include_relationship_props: List[str] = Field(default_factory=list)
    line_key: str = "child_config"
    include_substitutes: bool = False
    include_effectivity: bool = False
    name: str = ""
    note: str = ""


@bom_router.get(
    "/compare/summarized",
    summary="Compare two BOM trees in summarized row format",
)
async def compare_bom_summarized(
    left_type: str = Query(...),
    left_id: str = Query(...),
    right_type: str = Query(...),
    right_id: str = Query(...),
    max_levels: int = Query(10),
    effective_at: Optional[datetime] = Query(None),
    include_child_fields: bool = Query(False),
    include_relationship_props: Optional[List[str]] = Query(None),
    line_key: str = Query("child_config"),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await compare_bom(
        left_type=left_type, left_id=left_id,
        right_type=right_type, right_id=right_id,
        max_levels=max_levels, effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key, compare_mode="summarized",
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user, db=db,
    )
    return _compare_result_to_summarized_rows(result)


@bom_router.get(
    "/compare/summarized/export",
    summary="Export summarized BOM comparison",
)
async def compare_bom_summarized_export(
    left_type: str = Query(...),
    left_id: str = Query(...),
    right_type: str = Query(...),
    right_id: str = Query(...),
    max_levels: int = Query(10),
    effective_at: Optional[datetime] = Query(None),
    include_child_fields: bool = Query(False),
    include_relationship_props: Optional[List[str]] = Query(None),
    line_key: str = Query("child_config"),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    export_format: str = Query("csv"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_export_format(export_format)
    result = await compare_bom(
        left_type=left_type, left_id=left_id,
        right_type=right_type, right_id=right_id,
        max_levels=max_levels, effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key, compare_mode="summarized",
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user, db=db,
    )
    payload = _compare_result_to_summarized_rows(result)
    rows = payload["rows"]

    if export_format == "json":
        return JSONResponse(content=payload)
    if export_format == "csv":
        return StreamingResponse(
            io.BytesIO(_rows_to_csv(rows).encode()),
            media_type="text/csv",
            headers={"content-disposition": 'attachment; filename="bom-compare-summarized.csv"'},
        )
    md = _rows_to_markdown(rows)
    return StreamingResponse(
        io.BytesIO(md.encode()),
        media_type="text/markdown",
        headers={"content-disposition": 'attachment; filename="bom-compare-summarized.md"'},
    )


# ============================================================================
# Snapshot CRUD
# ============================================================================


@bom_router.post(
    "/compare/summarized/snapshots",
    summary="Create a summarized BOM comparison snapshot",
)
async def create_bom_summarized_snapshot(
    req: SnapshotCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await compare_bom(
        left_type=req.left_type, left_id=req.left_id,
        right_type=req.right_type, right_id=req.right_id,
        max_levels=req.max_levels, effective_at=req.effective_at,
        include_child_fields=req.include_child_fields,
        include_relationship_props=req.include_relationship_props or None,
        line_key=req.line_key, compare_mode="summarized",
        include_substitutes=req.include_substitutes,
        include_effectivity=req.include_effectivity,
        user=user, db=db,
    )
    payload = _compare_result_to_summarized_rows(result)
    snapshot_id = f"bom-compare-summarized-snapshot-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": now,
        "created_by": user.id,
        "name": req.name,
        "note": req.note,
        "compare": {
            "left_type": req.left_type,
            "left_id": req.left_id,
            "right_type": req.right_type,
            "right_id": req.right_id,
            "max_levels": req.max_levels,
            "effective_at": req.effective_at.isoformat() if req.effective_at else None,
            "include_child_fields": req.include_child_fields,
            "include_relationship_props": req.include_relationship_props or [],
            "line_key": req.line_key,
            "compare_mode": "summarized",
            "include_substitutes": req.include_substitutes,
            "include_effectivity": req.include_effectivity,
        },
        "summary": payload["summary"],
        "rows": payload["rows"],
        "row_total": len(payload["rows"]),
    }
    with _BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        _BOM_COMPARE_SUMMARIZED_SNAPSHOTS.append(snapshot)
    return snapshot


@bom_router.get(
    "/compare/summarized/snapshots/compare",
    summary="Compare two saved summarized snapshots",
)
async def compare_bom_summarized_snapshots(
    left_snapshot_id: str = Query(...),
    right_snapshot_id: str = Query(...),
):
    left = _find_snapshot(left_snapshot_id)
    right = _find_snapshot(right_snapshot_id)
    diff = _diff_snapshot_rows(left["rows"], right["rows"])
    return {"source": "snapshot_vs_snapshot", **diff}


@bom_router.get(
    "/compare/summarized/snapshots/compare/export",
    summary="Export snapshot vs snapshot diff",
)
async def compare_bom_summarized_snapshots_export(
    left_snapshot_id: str = Query(...),
    right_snapshot_id: str = Query(...),
    export_format: str = Query("csv"),
):
    _validate_export_format(export_format)
    left = _find_snapshot(left_snapshot_id)
    right = _find_snapshot(right_snapshot_id)
    diff = _diff_snapshot_rows(left["rows"], right["rows"])
    diff_result = {"source": "snapshot_vs_snapshot", **diff}
    return _export_diff(diff_result, export_format, "bom-compare-summarized-snapshot-diff")


@bom_router.get(
    "/compare/summarized/snapshots/{snapshot_id}/compare/current",
    summary="Compare a saved snapshot with current live BOM state",
)
async def compare_bom_summarized_snapshot_with_current(
    snapshot_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snap = _find_snapshot(snapshot_id)
    cmp = snap["compare"]
    result = await compare_bom(
        left_type=cmp["left_type"], left_id=cmp["left_id"],
        right_type=cmp["right_type"], right_id=cmp["right_id"],
        max_levels=cmp.get("max_levels", 10),
        effective_at=None,
        include_child_fields=cmp.get("include_child_fields", False),
        include_relationship_props=cmp.get("include_relationship_props") or None,
        line_key=cmp.get("line_key", "child_config"),
        compare_mode="summarized",
        include_substitutes=cmp.get("include_substitutes", False),
        include_effectivity=cmp.get("include_effectivity", False),
        user=user, db=db,
    )
    current_rows = _compare_result_to_summarized_rows(result)["rows"]
    diff = _diff_snapshot_rows(snap["rows"], current_rows)
    return {"source": "snapshot_vs_current", **diff}


@bom_router.get(
    "/compare/summarized/snapshots/{snapshot_id}/compare/current/export",
    summary="Export snapshot vs current diff",
)
async def compare_bom_summarized_snapshot_with_current_export(
    snapshot_id: str,
    export_format: str = Query("csv"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_export_format(export_format)
    snap = _find_snapshot(snapshot_id)
    cmp = snap["compare"]
    result = await compare_bom(
        left_type=cmp["left_type"], left_id=cmp["left_id"],
        right_type=cmp["right_type"], right_id=cmp["right_id"],
        max_levels=cmp.get("max_levels", 10),
        effective_at=None,
        include_child_fields=cmp.get("include_child_fields", False),
        include_relationship_props=cmp.get("include_relationship_props") or None,
        line_key=cmp.get("line_key", "child_config"),
        compare_mode="summarized",
        include_substitutes=cmp.get("include_substitutes", False),
        include_effectivity=cmp.get("include_effectivity", False),
        user=user, db=db,
    )
    current_rows = _compare_result_to_summarized_rows(result)["rows"]
    diff = _diff_snapshot_rows(snap["rows"], current_rows)
    diff_result = {"source": "snapshot_vs_current", **diff}
    return _export_diff(diff_result, export_format, "bom-compare-summarized-snapshot-diff")


@bom_router.get(
    "/compare/summarized/snapshots/{snapshot_id}/export",
    summary="Export a saved snapshot as CSV or Markdown",
)
async def export_bom_summarized_snapshot(
    snapshot_id: str,
    export_format: str = Query("csv"),
):
    _validate_export_format(export_format)
    snap = _find_snapshot(snapshot_id)
    rows = snap["rows"]

    if export_format == "json":
        return JSONResponse(content=snap)
    if export_format == "csv":
        return StreamingResponse(
            io.BytesIO(_rows_to_csv(rows).encode()),
            media_type="text/csv",
            headers={
                "content-disposition": f'attachment; filename="bom-compare-summarized-snapshot-{snapshot_id}.csv"'
            },
        )
    md = _rows_to_markdown(rows, f"BOM Compare Summarized Snapshot {snapshot_id}")
    return StreamingResponse(
        io.BytesIO(md.encode()),
        media_type="text/markdown",
        headers={
            "content-disposition": f'attachment; filename="bom-compare-summarized-snapshot-{snapshot_id}.md"'
        },
    )


@bom_router.get(
    "/compare/summarized/snapshots/{snapshot_id}",
    summary="Get a saved snapshot detail",
)
async def get_bom_summarized_snapshot(snapshot_id: str):
    return _find_snapshot(snapshot_id)


@bom_router.get(
    "/compare/summarized/snapshots",
    summary="List saved summarized snapshots",
)
async def list_bom_summarized_snapshots(
    created_by: Optional[int] = Query(None),
    name_contains: Optional[str] = Query(None),
    limit: int = Query(20),
    offset: int = Query(0),
):
    with _BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        filtered = list(_BOM_COMPARE_SUMMARIZED_SNAPSHOTS)

    if created_by is not None:
        filtered = [s for s in filtered if s.get("created_by") == created_by]
    if name_contains:
        lc = name_contains.lower()
        filtered = [s for s in filtered if lc in (s.get("name") or "").lower()]

    total = len(filtered)
    page = filtered[offset: offset + limit]

    snapshots = []
    for s in page:
        snapshots.append({
            "snapshot_id": s["snapshot_id"],
            "created_at": s.get("created_at"),
            "created_by": s.get("created_by"),
            "name": s.get("name"),
            "note": s.get("note"),
            "row_count": len(s.get("rows", [])),
            "rows": None,
        })

    return {
        "total": total,
        "count": len(snapshots),
        "limit": limit,
        "offset": offset,
        "snapshots": snapshots,
    }
