from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from ..models.meta_schema import ItemType, Property
from ..services.meta_schema_service import MetaSchemaService

schema_router = APIRouter(prefix="/meta", tags=["Metadata Schema"])


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Require admin or superuser role for meta schema management."""
    roles = set(user.roles or [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


# ============================================================================
# Request/Response Models
# ============================================================================


class ItemTypeCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=100, description="ItemType ID (e.g., 'Part', 'Document')")
    label: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    is_relationship: bool = Field(default=False)
    is_versionable: bool = Field(default=True)
    revision_scheme: str = Field(default="A-Z", max_length=50)
    permission_id: Optional[str] = Field(default=None, description="Default permission set ID")
    source_item_type_id: Optional[str] = Field(default=None, description="For relationships: source ItemType")
    related_item_type_id: Optional[str] = Field(default=None, description="For relationships: target ItemType")


class ItemTypeUpdateRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    is_versionable: Optional[bool] = None
    revision_scheme: Optional[str] = Field(default=None, max_length=50)
    permission_id: Optional[str] = None
    lifecycle_map_id: Optional[str] = None


class PropertyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: Optional[str] = Field(default=None, max_length=200)
    data_type: str = Field(default="string", description="string|integer|float|boolean|date|item|list|json")
    length: Optional[int] = Field(default=None, ge=1)
    is_required: bool = Field(default=False)
    default_value: Optional[str] = None
    ui_type: str = Field(default="text", max_length=50)
    ui_options: Optional[Dict[str, Any]] = None
    is_cad_synced: bool = Field(default=False)
    default_value_expression: Optional[str] = None
    data_source_id: Optional[str] = Field(default=None, description="For data_type='item': related ItemType")


class PropertyUpdateRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=200)
    data_type: Optional[str] = None
    length: Optional[int] = Field(default=None, ge=1)
    is_required: Optional[bool] = None
    default_value: Optional[str] = None
    ui_type: Optional[str] = Field(default=None, max_length=50)
    ui_options: Optional[Dict[str, Any]] = None
    is_cad_synced: Optional[bool] = None
    default_value_expression: Optional[str] = None
    data_source_id: Optional[str] = None


class PropertyResponse(BaseModel):
    id: str
    item_type_id: str
    name: str
    label: Optional[str]
    data_type: str
    length: Optional[int]
    is_required: bool
    default_value: Optional[str]
    ui_type: Optional[str]
    ui_options: Optional[Dict[str, Any]]
    is_cad_synced: bool
    data_source_id: Optional[str]


class ItemTypeResponse(BaseModel):
    id: str
    label: Optional[str]
    description: Optional[str]
    uuid: str
    is_relationship: bool
    is_versionable: bool
    revision_scheme: Optional[str]
    permission_id: Optional[str]
    lifecycle_map_id: Optional[str]
    source_item_type_id: Optional[str]
    related_item_type_id: Optional[str]
    property_count: int = 0


class ItemTypeDetailResponse(ItemTypeResponse):
    properties: List[PropertyResponse] = Field(default_factory=list)


# ============================================================================
# ItemType CRUD Endpoints
# ============================================================================


@schema_router.get("/item-types", response_model=Dict[str, Any])
async def list_item_types(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List all ItemTypes (public read)."""
    item_types = db.query(ItemType).order_by(ItemType.id.asc()).all()
    return {
        "total": len(item_types),
        "items": [
            ItemTypeResponse(
                id=it.id,
                label=it.label,
                description=it.description,
                uuid=it.uuid or "",
                is_relationship=bool(it.is_relationship),
                is_versionable=bool(it.is_versionable),
                revision_scheme=it.revision_scheme,
                permission_id=it.permission_id,
                lifecycle_map_id=it.lifecycle_map_id,
                source_item_type_id=it.source_item_type_id,
                related_item_type_id=it.related_item_type_id,
                property_count=len(it.properties or []),
            ).model_dump()
            for it in item_types
        ],
    }


@schema_router.get("/item-types/{item_type_id}", response_model=ItemTypeDetailResponse)
async def get_item_type(
    item_type_id: str,
    db: Session = Depends(get_db),
) -> ItemTypeDetailResponse:
    """Get ItemType with all properties (public read)."""
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    return ItemTypeDetailResponse(
        id=item_type.id,
        label=item_type.label,
        description=item_type.description,
        uuid=item_type.uuid or "",
        is_relationship=bool(item_type.is_relationship),
        is_versionable=bool(item_type.is_versionable),
        revision_scheme=item_type.revision_scheme,
        permission_id=item_type.permission_id,
        lifecycle_map_id=item_type.lifecycle_map_id,
        source_item_type_id=item_type.source_item_type_id,
        related_item_type_id=item_type.related_item_type_id,
        property_count=len(item_type.properties or []),
        properties=[
            PropertyResponse(
                id=p.id,
                item_type_id=p.item_type_id,
                name=p.name,
                label=p.label,
                data_type=p.data_type or "string",
                length=p.length,
                is_required=bool(p.is_required),
                default_value=p.default_value,
                ui_type=p.ui_type,
                ui_options=p.ui_options,
                is_cad_synced=bool(p.is_cad_synced),
                data_source_id=p.data_source_id,
            )
            for p in item_type.properties
        ],
    )


@schema_router.post("/item-types", response_model=ItemTypeResponse)
async def create_item_type(
    req: ItemTypeCreateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemTypeResponse:
    """Create a new ItemType (admin only)."""
    existing = db.query(ItemType).filter(ItemType.id == req.id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"ItemType '{req.id}' already exists")

    item_type = ItemType(
        id=req.id,
        label=req.label or req.id,
        description=req.description,
        uuid=str(uuid.uuid4()),
        is_relationship=req.is_relationship,
        is_versionable=req.is_versionable,
        version_control_enabled=req.is_versionable,
        revision_scheme=req.revision_scheme,
        permission_id=req.permission_id,
        source_item_type_id=req.source_item_type_id,
        related_item_type_id=req.related_item_type_id,
    )
    db.add(item_type)
    db.commit()
    db.refresh(item_type)

    return ItemTypeResponse(
        id=item_type.id,
        label=item_type.label,
        description=item_type.description,
        uuid=item_type.uuid,
        is_relationship=bool(item_type.is_relationship),
        is_versionable=bool(item_type.is_versionable),
        revision_scheme=item_type.revision_scheme,
        permission_id=item_type.permission_id,
        lifecycle_map_id=item_type.lifecycle_map_id,
        source_item_type_id=item_type.source_item_type_id,
        related_item_type_id=item_type.related_item_type_id,
        property_count=0,
    )


@schema_router.patch("/item-types/{item_type_id}", response_model=ItemTypeResponse)
async def update_item_type(
    item_type_id: str,
    req: ItemTypeUpdateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemTypeResponse:
    """Update an ItemType (admin only)."""
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    if req.label is not None:
        item_type.label = req.label
    if req.description is not None:
        item_type.description = req.description
    if req.is_versionable is not None:
        item_type.is_versionable = req.is_versionable
        item_type.version_control_enabled = req.is_versionable
    if req.revision_scheme is not None:
        item_type.revision_scheme = req.revision_scheme
    if req.permission_id is not None:
        item_type.permission_id = req.permission_id
    if req.lifecycle_map_id is not None:
        item_type.lifecycle_map_id = req.lifecycle_map_id

    db.add(item_type)
    db.commit()
    db.refresh(item_type)

    return ItemTypeResponse(
        id=item_type.id,
        label=item_type.label,
        description=item_type.description,
        uuid=item_type.uuid or "",
        is_relationship=bool(item_type.is_relationship),
        is_versionable=bool(item_type.is_versionable),
        revision_scheme=item_type.revision_scheme,
        permission_id=item_type.permission_id,
        lifecycle_map_id=item_type.lifecycle_map_id,
        source_item_type_id=item_type.source_item_type_id,
        related_item_type_id=item_type.related_item_type_id,
        property_count=len(item_type.properties or []),
    )


# ============================================================================
# Property CRUD Endpoints
# ============================================================================


@schema_router.post("/item-types/{item_type_id}/properties", response_model=PropertyResponse)
async def create_property(
    item_type_id: str,
    req: PropertyCreateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PropertyResponse:
    """Create a new Property for an ItemType (admin only)."""
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    # Check for duplicate property name
    existing = db.query(Property).filter(
        Property.item_type_id == item_type_id,
        Property.name == req.name
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Property '{req.name}' already exists on ItemType '{item_type_id}'")

    prop = Property(
        id=str(uuid.uuid4()),
        item_type_id=item_type_id,
        name=req.name,
        label=req.label or req.name,
        data_type=req.data_type,
        length=req.length,
        is_required=req.is_required,
        default_value=req.default_value,
        ui_type=req.ui_type,
        ui_options=req.ui_options,
        is_cad_synced=req.is_cad_synced,
        default_value_expression=req.default_value_expression,
        data_source_id=req.data_source_id,
    )
    db.add(prop)

    # Invalidate cached schema
    item_type.properties_schema = None
    db.add(item_type)

    db.commit()
    db.refresh(prop)

    return PropertyResponse(
        id=prop.id,
        item_type_id=prop.item_type_id,
        name=prop.name,
        label=prop.label,
        data_type=prop.data_type or "string",
        length=prop.length,
        is_required=bool(prop.is_required),
        default_value=prop.default_value,
        ui_type=prop.ui_type,
        ui_options=prop.ui_options,
        is_cad_synced=bool(prop.is_cad_synced),
        data_source_id=prop.data_source_id,
    )


@schema_router.patch("/item-types/{item_type_id}/properties/{property_id}", response_model=PropertyResponse)
async def update_property(
    item_type_id: str,
    property_id: str,
    req: PropertyUpdateRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PropertyResponse:
    """Update a Property (admin only)."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop or prop.item_type_id != item_type_id:
        raise HTTPException(status_code=404, detail="Property not found")

    if req.label is not None:
        prop.label = req.label
    if req.data_type is not None:
        prop.data_type = req.data_type
    if req.length is not None:
        prop.length = req.length
    if req.is_required is not None:
        prop.is_required = req.is_required
    if req.default_value is not None:
        prop.default_value = req.default_value
    if req.ui_type is not None:
        prop.ui_type = req.ui_type
    if req.ui_options is not None:
        prop.ui_options = req.ui_options
    if req.is_cad_synced is not None:
        prop.is_cad_synced = req.is_cad_synced
    if req.default_value_expression is not None:
        prop.default_value_expression = req.default_value_expression
    if req.data_source_id is not None:
        prop.data_source_id = req.data_source_id

    db.add(prop)

    # Invalidate cached schema
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if item_type:
        item_type.properties_schema = None
        db.add(item_type)

    db.commit()
    db.refresh(prop)

    return PropertyResponse(
        id=prop.id,
        item_type_id=prop.item_type_id,
        name=prop.name,
        label=prop.label,
        data_type=prop.data_type or "string",
        length=prop.length,
        is_required=bool(prop.is_required),
        default_value=prop.default_value,
        ui_type=prop.ui_type,
        ui_options=prop.ui_options,
        is_cad_synced=bool(prop.is_cad_synced),
        data_source_id=prop.data_source_id,
    )


@schema_router.delete("/item-types/{item_type_id}/properties/{property_id}", response_model=Dict[str, Any])
async def delete_property(
    item_type_id: str,
    property_id: str,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a Property (admin only)."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop or prop.item_type_id != item_type_id:
        raise HTTPException(status_code=404, detail="Property not found")

    db.delete(prop)

    # Invalidate cached schema
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if item_type:
        item_type.properties_schema = None
        db.add(item_type)

    db.commit()
    return {"ok": True, "id": property_id}


# ============================================================================
# Schema Management Endpoints
# ============================================================================


@schema_router.post("/item-types/{item_type_id}/refresh-schema", response_model=Dict[str, Any])
async def refresh_item_type_schema(
    item_type_id: str,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Force refresh the cached properties_schema from Property definitions.
    Use this after modifying properties to ensure schema/ETag consistency.
    Admin only.
    """
    service = MetaSchemaService(db)
    try:
        schema = service.update_cached_schema(item_type_id)
        etag = service.get_schema_etag(item_type_id)
        return {
            "ok": True,
            "item_type_id": item_type_id,
            "etag": etag,
            "property_count": len(schema.get("properties", {})),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@schema_router.get("/item-types/{item_type_id}/schema")
async def get_item_type_schema(
    item_type_id: str,
    response: Response,
    if_none_match: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Get the JSON Schema for an ItemType.
    Supports HTTP ETag caching.
    """
    service = MetaSchemaService(db)
    try:
        # Check ETag first to avoid large payload transfer if not modified
        etag = service.get_schema_etag(item_type_id)

        # Determine if we can return 304 Not Modified
        # Note: If-None-Match can be a list of tags or *, strict parsing might be needed
        # but simple string equality covers 99% of simple browser clients.
        if if_none_match and if_none_match.replace('"', "") == etag:
            response.status_code = 304
            return None

        # Return full schema with ETag header
        response.headers["ETag"] = f'"{etag}"'
        schema = service.get_json_schema(item_type_id)
        return schema

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
