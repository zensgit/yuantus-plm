from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json
from datetime import datetime
from pydantic import BaseModel, Field
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.bom_conversion_service import BOMConversionService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.api.dependencies.auth import CurrentUser, get_current_user

bom_tree_router = APIRouter(prefix="/bom", tags=["BOM"])


# ============================================================================
# Helpers
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


# ============================================================================
# Request/Response Models
# ============================================================================


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


# ============================================================================
# BOM Structure Read APIs
# ============================================================================


@bom_tree_router.get("/{item_id}/effective", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=404, detail=str(e)) from e


@bom_tree_router.get("/version/{version_id}", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============================================================================
# MBOM Conversion
# ============================================================================


@bom_tree_router.post(
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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    return ConvertBomResponse(
        ok=True,
        source_root_id=request.root_id,
        mbom_root_id=mbom_root.id,
        mbom_root_type=mbom_root.item_type_id,
        mbom_root_config_id=mbom_root.config_id,
    )


# ============================================================================
# BOM Tree (EBOM / MBOM)
# ============================================================================


@bom_tree_router.get("/{parent_id}/tree", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=404, detail=str(e)) from e


@bom_tree_router.get("/mbom/{parent_id}/tree", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=404, detail=str(e)) from e
