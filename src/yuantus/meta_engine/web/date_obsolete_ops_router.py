"""CAD-PDM C3 — admin ops for date-obsolete where-used impact flags (Slice 2).

The async analogue of a review surface: list / inspect / acknowledge the depth-1 parent
flags raised when a date effectivity expires. Read + ack only — never re-triggers obsolete.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import (
    CurrentUser,
    get_current_user,
    require_admin_permission,
)
from yuantus.database import get_db
from yuantus.meta_engine.models.date_obsolete import DateObsoleteImpact

date_obsolete_ops_router = APIRouter(tags=["CADPDM"])

_IMPACT_STATES = {"open", "acknowledged"}


def _impact(row: DateObsoleteImpact) -> Dict[str, Any]:
    return {
        "id": row.id,
        "effectivity_id": row.effectivity_id,
        "child_item_id": row.child_item_id,
        "parent_item_id": row.parent_item_id,
        "child_obsoleted": row.child_obsoleted,
        "reason": row.reason,
        "state": row.state,
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "acknowledged_by_id": row.acknowledged_by_id,
        "properties": row.properties,
    }


@date_obsolete_ops_router.get("/cadpdm/date-obsolete-impacts")
async def list_date_obsolete_impacts(
    state: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_admin_permission(user)
    if state is not None and state not in _IMPACT_STATES:
        raise HTTPException(
            status_code=422,
            detail={"code": "cadpdm_date_obsolete_invalid_state",
                    "message": f"state must be one of {sorted(_IMPACT_STATES)}"},
        )
    q = db.query(DateObsoleteImpact)
    if state is not None:
        q = q.filter(DateObsoleteImpact.state == state)
    rows = q.order_by(DateObsoleteImpact.detected_at.desc()).limit(limit).all()
    return {"count": len(rows), "rows": [_impact(r) for r in rows]}


@date_obsolete_ops_router.get("/cadpdm/date-obsolete-impacts/{impact_id}")
async def get_date_obsolete_impact(
    impact_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_admin_permission(user)
    row = db.get(DateObsoleteImpact, impact_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "cadpdm_date_obsolete_not_found", "message": "impact not found"},
        )
    return _impact(row)


@date_obsolete_ops_router.post("/cadpdm/date-obsolete-impacts/{impact_id}/acknowledge")
async def acknowledge_date_obsolete_impact(
    impact_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_admin_permission(user)
    row = db.get(DateObsoleteImpact, impact_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "cadpdm_date_obsolete_not_found", "message": "impact not found"},
        )
    if row.state != "acknowledged":
        row.state = "acknowledged"
        row.acknowledged_at = datetime.utcnow()
        row.acknowledged_by_id = int(user.id)
        db.commit()
    return _impact(row)
