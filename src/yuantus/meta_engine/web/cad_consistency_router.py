"""WP1.3 CAD 2D/3D staleness API (item-centered, zero traversal).

GET  /cad/items/{item_id}/staleness            read the materialized verdict
POST /cad/items/{item_id}/staleness/recompute  recompute (pin provenance + flags)

The assembly-tree ``stale-drawings`` scan is intentionally deferred to after
WP1.2 traversal (D6); there is no ``/documents/...`` surface (WP1.0 D4).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.cad_consistency_service import CadConsistencyService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService

cad_consistency_router = APIRouter(prefix="/cad", tags=["CAD"])


def _require_item(db: Session, item_id: str) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return item


def _require_permission(
    db: Session, item: Item, action: AMLAction, user: CurrentUser
) -> None:
    perm = MetaPermissionService(db)
    if not perm.check_permission(
        item.item_type_id,
        action,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")


@cad_consistency_router.get(
    "/items/{item_id}/staleness", response_model=Dict[str, Any]
)
async def get_item_staleness(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    item = _require_item(db, item_id)
    _require_permission(db, item, AMLAction.get, user)
    return CadConsistencyService(db).get_staleness(item_id)


@cad_consistency_router.post(
    "/items/{item_id}/staleness/recompute", response_model=Dict[str, Any]
)
async def recompute_item_staleness(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    item = _require_item(db, item_id)
    _require_permission(db, item, AMLAction.update, user)
    return CadConsistencyService(db).recompute(item_id)
