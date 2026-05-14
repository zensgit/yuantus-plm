"""
Legacy ECM Router (Compatibility Shim)
======================================
DEPRECATED: This router exists only for backward compatibility during the
/ecm → /eco convergence period.  All write operations are delegated to the
canonical ECOService via LegacyEcmCompatService.

New features MUST NOT be added to this router.
New consumers MUST NOT call /ecm endpoints.

Sunset target: remove after PR-4 confirms zero /ecm traffic.
See: scripts/audit_ecm_legacy.py for the full legacy surface audit.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.services.legacy_ecm_compat_service import (
    LegacyEcmCompatService,
)
from yuantus.api.dependencies.auth import (
    get_current_user_id_optional as get_current_user_id,
)


change_router = APIRouter(
    prefix="/ecm",
    tags=["Change Management (Legacy)"],
    deprecated=True,
)

_DEPRECATION_HEADERS = {
    "Deprecation": "true",
    "Sunset": "2026-07-01",
    "Link": '</api/v1/eco>; rel="successor-version"',
}


@change_router.get("/items/{item_id}/impact")
def get_impact_analysis(item_id: str, db: Session = Depends(get_db)):
    """[DEPRECATED] Use GET /eco/{eco_id}/impact or GET /impact/where-used instead."""
    service = LegacyEcmCompatService(db)
    result = service.get_impact_analysis(item_id)
    return JSONResponse(content=result, headers=_DEPRECATION_HEADERS)


@change_router.get("/eco/{eco_id}/affected-items")
def get_affected_items(eco_id: str, db: Session = Depends(get_db)):
    """[DEPRECATED] ECO product binding is now via POST /eco/{eco_id}/bind-product.

    Returns the bound product_id as a single-element list for backward compat.
    """
    service = LegacyEcmCompatService(db)
    eco = service.eco_service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    items = []
    if eco.product_id:
        items.append({"product_id": eco.product_id, "action": "Change"})

    return JSONResponse(content=items, headers=_DEPRECATION_HEADERS)


@change_router.post("/eco/{eco_id}/affected-items")
def add_affected_item(
    eco_id: str,
    target_item_id: str = Body(..., embed=True),
    action: str = Body("Change", embed=True),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """[DEPRECATED] Use POST /eco/{eco_id}/bind-product instead."""
    service = LegacyEcmCompatService(db)
    try:
        result = service.add_affected_item_compat(eco_id, target_item_id, action, user_id)
        db.commit()
        return JSONResponse(content=result, headers=_DEPRECATION_HEADERS)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@change_router.post("/eco/{eco_id}/execute")
def execute_eco(
    eco_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """[DEPRECATED] Use POST /eco/{eco_id}/apply instead.

    Requires ECO to be in 'approved' state.  The old behavior of executing
    Release/Revise/New Generation on affected items directly is no longer
    supported — use the canonical /eco approval workflow.
    """
    service = LegacyEcmCompatService(db)
    try:
        result = service.execute_eco_compat(eco_id, user_id)
        db.commit()
        return JSONResponse(content=result, headers=_DEPRECATION_HEADERS)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
