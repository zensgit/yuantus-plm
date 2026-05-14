"""PLM Box core item and content endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.models import BoxContent, BoxItem
from yuantus.meta_engine.box.service import BoxService


box_core_router = APIRouter(prefix="/box", tags=["PLM Box"])


class BoxCreateRequest(BaseModel):
    name: str
    box_type: str = "box"
    description: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    dimension_unit: str = "mm"
    tare_weight: Optional[float] = None
    max_gross_weight: Optional[float] = None
    weight_unit: str = "kg"
    material: Optional[str] = None
    barcode: Optional[str] = None
    max_quantity: Optional[int] = None
    cost: Optional[float] = None
    product_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


def _box_dict(box: BoxItem) -> Dict[str, Any]:
    return {
        "id": box.id,
        "name": box.name,
        "description": box.description,
        "box_type": box.box_type,
        "state": box.state,
        "width": box.width,
        "height": box.height,
        "depth": box.depth,
        "dimension_unit": box.dimension_unit,
        "tare_weight": box.tare_weight,
        "max_gross_weight": box.max_gross_weight,
        "weight_unit": box.weight_unit,
        "material": box.material,
        "barcode": box.barcode,
        "max_quantity": box.max_quantity,
        "cost": box.cost,
        "product_id": box.product_id,
        "is_active": box.is_active,
    }


def _content_dict(content: BoxContent) -> Dict[str, Any]:
    return {
        "id": content.id,
        "box_id": content.box_id,
        "item_id": content.item_id,
        "quantity": content.quantity,
        "lot_serial": content.lot_serial,
        "note": content.note,
    }


@box_core_router.post("/items")
def create_box_item(
    request: BoxCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        box = service.create_box(
            name=request.name,
            box_type=request.box_type,
            description=request.description,
            width=request.width,
            height=request.height,
            depth=request.depth,
            dimension_unit=request.dimension_unit,
            tare_weight=request.tare_weight,
            max_gross_weight=request.max_gross_weight,
            weight_unit=request.weight_unit,
            material=request.material,
            barcode=request.barcode,
            max_quantity=request.max_quantity,
            cost=request.cost,
            product_id=request.product_id,
            properties=request.properties,
            created_by_id=user.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **_box_dict(box)}


@box_core_router.get("/items")
def list_box_items(
    box_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    boxes = service.list_boxes(box_type=box_type, state=state, product_id=product_id)
    return {"items": [_box_dict(b) for b in boxes], "count": len(boxes)}


@box_core_router.get("/items/{box_id}")
def get_box_item(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    box = service.get_box(box_id)
    if box is None:
        raise HTTPException(status_code=404, detail=f"Box '{box_id}' not found")
    return _box_dict(box)


@box_core_router.get("/items/{box_id}/contents")
def list_box_contents(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    box = service.get_box(box_id)
    if box is None:
        raise HTTPException(status_code=404, detail=f"Box '{box_id}' not found")
    contents = service.list_contents(box_id)
    return {"contents": [_content_dict(c) for c in contents], "count": len(contents)}


@box_core_router.get("/items/{box_id}/export-meta")
def export_box_meta(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        meta = service.export_meta(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return meta
