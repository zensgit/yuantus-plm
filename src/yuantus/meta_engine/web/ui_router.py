from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
from yuantus.database import get_db
from ..views.models import Form, GridView
from ..views.mapping import ViewMapping
from ..models.meta_schema import ItemType, PropertyDefinition
from fastapi import Response

# 扩展原有的 meta_router 或者新建一个 ui_router
ui_router = APIRouter(prefix="/ui", tags=["Meta UI"])

# JSON Schema type mapping
_TYPE_MAP = {
    "string": {"type": "string"},
    "text": {"type": "string"},
    "integer": {"type": "integer"},
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "decimal": {"type": "number"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
    "bool": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "datetime": {"type": "string", "format": "date-time"},
    "json": {"type": "object"},
    "list": {"type": "array"},
    "item": {"type": "string", "format": "uuid"},  # Reference to another Item
}

_FORM_CACHE: dict[
    Tuple[str, str, str, Optional[str], bool, bool], Tuple[str, Dict[str, Any]]
] = {}
_GRID_CACHE: dict[Tuple[str, str, str, Optional[str]], Tuple[str, Dict[str, Any]]] = {}


def _select_mapping(
    mappings: List[ViewMapping],
    identity_id: str,
    device_type: str,
) -> Optional[ViewMapping]:
    mapping = next(
        (
            m
            for m in mappings
            if m.identity_id == identity_id and m.device_type == device_type
        ),
        None,
    )
    if not mapping:
        mapping = next(
            (m for m in mappings if m.identity_id == identity_id), None
        ) or next((m for m in mappings if m.identity_id in (None, "world")), None)
    return mapping


@ui_router.get("/form/{item_type_id}")
async def get_form_definition(
    item_type_id: str,
    identity_id: str = "world",
    device_type: str = "desktop",
    view_id: Optional[str] = None,
    include_layout: bool = True,
    include_validation: bool = False,
    response: Response = None,
    db: Session = Depends(get_db),
):
    """
    获取指定 ItemType 的最佳表单定义
    包含逻辑：Role-based Form Selection (优先级匹配)
    """
    cache_key = (
        item_type_id,
        identity_id,
        device_type,
        view_id,
        include_layout,
        include_validation,
    )
    if cache_key in _FORM_CACHE:
        etag, payload = _FORM_CACHE[cache_key]
        if response is not None:
            response.headers["Cache-Control"] = "max-age=30"
            response.headers["ETag"] = etag
        return payload

    mappings = (
        db.execute(
            select(ViewMapping)
            .where(ViewMapping.item_type_id == item_type_id)
            .order_by(ViewMapping.sort_order.desc())
        )
        .scalars()
        .all()
    )

    mapping: Optional[ViewMapping]
    if view_id:
        mapping = db.get(ViewMapping, view_id)
    else:
        mapping = _select_mapping(mappings, identity_id, device_type)

    if not mapping or not mapping.form_id:
        raise HTTPException(status_code=404, detail="No form defined for this type")

    form = db.get(Form, mapping.form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    resp = {
        "id": form.id,
        "name": form.name,
        "fields": [
            {
                "property": f.property_name,
                "label": f.label,
                "control": f.control_type,
                **(
                    {"layout": {"x": f.x_pos, "y": f.y_pos, "w": f.width}}
                    if include_layout
                    else {}
                ),
                **(
                    {
                        "validation": {
                            "required": (
                                True
                                if include_validation and getattr(f, "required", None)
                                else None
                            )
                        }
                    }
                    if include_validation
                    else {}
                ),
            }
            for f in form.fields
        ],
    }
    etag = hashlib.sha1(json.dumps(resp, sort_keys=True).encode()).hexdigest()
    _FORM_CACHE[cache_key] = (etag, resp)
    if response is not None:
        response.headers["Cache-Control"] = "max-age=30"
        response.headers["ETag"] = etag
    return resp


@ui_router.get("/grid/{item_type_id}")
async def get_grid_definition(
    item_type_id: str,
    identity_id: str = "world",
    device_type: str = "desktop",
    view_id: Optional[str] = None,
    response: Response = None,
    db: Session = Depends(get_db),
):
    """
    获取指定 ItemType 的最佳 Grid 定义
    """
    cache_key = (item_type_id, identity_id, device_type, view_id)
    if cache_key in _GRID_CACHE:
        etag, payload = _GRID_CACHE[cache_key]
        if response is not None:
            response.headers["Cache-Control"] = "max-age=30"
            response.headers["ETag"] = etag
        return payload

    mappings = (
        db.execute(
            select(ViewMapping)
            .where(ViewMapping.item_type_id == item_type_id)
            .order_by(ViewMapping.sort_order.desc())
        )
        .scalars()
        .all()
    )

    mapping: Optional[ViewMapping]
    if view_id:
        mapping = db.get(ViewMapping, view_id)
    else:
        mapping = _select_mapping(mappings, identity_id, device_type)

    if not mapping or not mapping.grid_view_id:
        raise HTTPException(status_code=404, detail="No grid defined for this type")

    grid = db.get(GridView, mapping.grid_view_id)
    if not grid:
        raise HTTPException(status_code=404, detail="Grid not found")

    resp = {
        "id": grid.id,
        "name": grid.name,
        "columns": [
            {
                "property": c.property_name,
                "label": c.label,
                "width": c.width,
                "order": c.sort_order,
            }
            for c in sorted(grid.columns, key=lambda c: c.sort_order or 0)
        ],
    }
    etag = hashlib.sha1(json.dumps(resp, sort_keys=True).encode()).hexdigest()
    _GRID_CACHE[cache_key] = (etag, resp)
    if response is not None:
        response.headers["Cache-Control"] = "max-age=30"
        response.headers["ETag"] = etag
    return resp


# JSON Schema Cache
_SCHEMA_CACHE: dict[str, Tuple[str, Dict[str, Any]]] = {}


@ui_router.get("/schema/{item_type_id}")
async def get_ui_schema(
    item_type_id: str,
    response: Response = None,
    db: Session = Depends(get_db),
):
    """
    获取 ItemType 的 JSON Schema + UI Schema (ADR-007)

    从 PropertyDefinition 派生，支持 AutoForm 直接消费

    Returns:
        {
            "json_schema": {...},  # JSON Schema for validation
            "ui_schema": {...},    # UI hints for rendering
            "version": "1.0.0",
            "etag": "abc123"
        }
    """
    # Check cache
    if item_type_id in _SCHEMA_CACHE:
        etag, payload = _SCHEMA_CACHE[item_type_id]
        if response is not None:
            response.headers["Cache-Control"] = "max-age=60"
            response.headers["ETag"] = etag
        return payload

    # Get ItemType
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(
            status_code=404, detail=f"ItemType '{item_type_id}' not found"
        )

    # Build JSON Schema
    json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": item_type.label or item_type.id,
        "description": item_type.description or "",
        "properties": {},
        "required": [],
    }

    # Build UI Schema
    ui_schema = {
        "ui:order": [],
    }

    # Add standard Item fields
    json_schema["properties"]["number"] = {
        "type": "string",
        "maxLength": 64,
        "title": "编号",
    }
    json_schema["properties"]["name"] = {
        "type": "string",
        "maxLength": 256,
        "title": "名称",
    }
    json_schema["required"].extend(["number", "name"])
    ui_schema["ui:order"].extend(["number", "name"])
    ui_schema["number"] = {"ui:readonly": False}
    ui_schema["name"] = {"ui:readonly": False}

    # Process PropertyDefinitions
    for prop in item_type.properties:
        prop_name = prop.name
        prop_schema = _build_property_schema(prop)
        json_schema["properties"][prop_name] = prop_schema

        if prop.is_required:
            json_schema["required"].append(prop_name)

        # UI Schema hints
        ui_hints = _build_ui_hints(prop)
        if ui_hints:
            ui_schema[prop_name] = ui_hints

        ui_schema["ui:order"].append(prop_name)

    # Add state field (read-only)
    json_schema["properties"]["state"] = {
        "type": "string",
        "title": "状态",
        "readOnly": True,
    }
    ui_schema["state"] = {"ui:readonly": True, "ui:widget": "badge"}
    ui_schema["ui:order"].append("state")

    # Generate version and ETag
    version = "1.0.0"
    resp = {
        "json_schema": json_schema,
        "ui_schema": ui_schema,
        "item_type": {
            "id": item_type.id,
            "name": item_type.id,
            "label": item_type.label,
            "is_versionable": item_type.is_versionable,
        },
        "version": version,
    }

    etag = hashlib.sha1(json.dumps(resp, sort_keys=True).encode()).hexdigest()[:16]
    resp["etag"] = etag

    # Cache
    _SCHEMA_CACHE[item_type_id] = (etag, resp)

    if response is not None:
        response.headers["Cache-Control"] = "max-age=60"
        response.headers["ETag"] = etag

    return resp


def _build_property_schema(prop: PropertyDefinition) -> Dict[str, Any]:
    """从 PropertyDefinition 构建 JSON Schema 属性"""
    data_type = (prop.data_type or "string").lower()
    schema = _TYPE_MAP.get(data_type, {"type": "string"}).copy()

    schema["title"] = prop.label or prop.name

    if prop.description:
        schema["description"] = prop.description

    # String constraints
    if data_type in ("string", "text") and prop.length:
        schema["maxLength"] = prop.length

    # Default value
    if prop.default_value is not None:
        schema["default"] = prop.default_value

    # Pattern/Regex
    if prop.pattern:
        schema["pattern"] = prop.pattern

    # List source (enum)
    if prop.list_source_id:
        # Could fetch list values here, for now mark as having options
        schema["x-list-source"] = prop.list_source_id

    # Readonly
    if prop.is_readonly:
        schema["readOnly"] = True

    return schema


def _build_ui_hints(prop: PropertyDefinition) -> Dict[str, Any]:
    """从 PropertyDefinition 构建 UI hints"""
    hints = {}
    data_type = (prop.data_type or "string").lower()

    # Widget selection based on type
    if data_type == "text":
        hints["ui:widget"] = "textarea"
    elif data_type == "boolean":
        hints["ui:widget"] = "checkbox"
    elif data_type == "date":
        hints["ui:widget"] = "date"
    elif data_type == "datetime":
        hints["ui:widget"] = "datetime"
    elif data_type in ("integer", "float", "decimal", "number"):
        hints["ui:widget"] = "updown"
    elif data_type == "item":
        hints["ui:widget"] = "item-picker"
        if prop.data_source:
            hints["ui:options"] = {"itemType": prop.data_source}

    # Readonly
    if prop.is_readonly:
        hints["ui:readonly"] = True

    # Hidden
    if prop.is_hidden:
        hints["ui:widget"] = "hidden"

    # Help text
    if prop.description:
        hints["ui:help"] = prop.description

    # Placeholder
    if prop.placeholder:
        hints["ui:placeholder"] = prop.placeholder

    return hints


@ui_router.delete("/schema/cache")
async def clear_schema_cache():
    """清除 Schema 缓存"""
    global _SCHEMA_CACHE, _FORM_CACHE, _GRID_CACHE
    _SCHEMA_CACHE.clear()
    _FORM_CACHE.clear()
    _GRID_CACHE.clear()
    return {"status": "ok", "message": "Cache cleared"}
