"""
ECO core router.

This router owns the remaining core ECO endpoints after the approval, stage,
workflow, impact/apply, change-analysis, and lifecycle surfaces were split out.
Route order matters: static routes such as /kanban must stay before /{eco_id}.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.models.eco import ECOState
from yuantus.meta_engine.services.eco_service import ECOService, ECOStageService

eco_core_router = APIRouter(prefix="/eco", tags=["ECO"])


class ECOCreate(BaseModel):
    """Schema for creating an ECO."""

    name: str = Field(..., min_length=1, max_length=100)
    eco_type: str = Field(default="bom")
    product_id: Optional[str] = None
    description: Optional[str] = None
    priority: str = Field(default="normal")


class ECOUpdate(BaseModel):
    """Schema for updating an ECO."""

    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    effectivity_date: Optional[datetime] = None


class BindProductRequest(BaseModel):
    """Schema for binding a product to an ECO."""

    product_id: str = Field(..., min_length=1)
    create_target_revision: bool = Field(default=False)


@eco_core_router.get("/kanban", response_model=Dict[str, Any])
async def get_kanban_view(
    product_id: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Get ECOs organized by stage for Kanban view.

    Returns:
        Dict with stages as keys and ECO lists as values.
    """
    stage_service = ECOStageService(db)
    eco_service = ECOService(db)

    stages = stage_service.list_stages()

    result = {"stages": [], "ecos_by_stage": {}}

    for stage in stages:
        stage_data = {
            "id": stage.id,
            "name": stage.name,
            "sequence": stage.sequence,
            "fold": stage.fold,
            "approval_type": stage.approval_type,
            "sla_hours": stage.sla_hours,
        }
        result["stages"].append(stage_data)

        ecos = eco_service.list_ecos(stage_id=stage.id, product_id=product_id)
        result["ecos_by_stage"][stage.id] = [eco.to_dict() for eco in ecos]

    return result


@eco_core_router.post("", response_model=Dict[str, Any])
async def create_eco(
    data: ECOCreate,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Create a new ECO.

    Args:
        data: ECO creation data.
        user_id: User creating the ECO.

    Returns:
        Created ECO data.
    """
    service = ECOService(db)
    try:
        eco = service.create_eco(
            name=data.name,
            eco_type=data.eco_type,
            product_id=data.product_id,
            description=data.description,
            priority=data.priority,
            user_id=user_id,
        )
        db.commit()
        return eco.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_core_router.get("", response_model=List[Dict[str, Any]])
async def list_ecos(
    state: Optional[str] = None,
    stage_id: Optional[str] = None,
    product_id: Optional[str] = None,
    created_by_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List ECOs with optional filters.

    Args:
        state: Filter by state (draft, progress, approved, done, canceled).
        stage_id: Filter by stage.
        product_id: Filter by product.
        created_by_id: Filter by creator.
        limit: Max results.
        offset: Pagination offset.

    Returns:
        List of ECOs.
    """
    service = ECOService(db)
    ecos = service.list_ecos(
        state=state,
        stage_id=stage_id,
        product_id=product_id,
        created_by_id=created_by_id,
        limit=limit,
        offset=offset,
    )
    return [eco.to_dict() for eco in ecos]


@eco_core_router.get("/{eco_id}", response_model=Dict[str, Any])
async def get_eco(eco_id: str, db: Session = Depends(get_db)):
    """Get ECO by ID."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")
    return eco.to_dict()


@eco_core_router.post("/{eco_id}/bind-product", response_model=Dict[str, Any])
async def bind_product_to_eco(
    eco_id: str,
    data: BindProductRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Bind a product to an ECO."""
    service = ECOService(db)
    try:
        eco = service.bind_product(
            eco_id,
            data.product_id,
            user_id,
            create_target_revision=data.create_target_revision,
        )
        db.commit()
        return eco.to_dict()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_core_router.put("/{eco_id}", response_model=Dict[str, Any])
async def update_eco(
    eco_id: str,
    data: ECOUpdate,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Update an ECO."""
    service = ECOService(db)
    updates = data.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        eco = service.update_eco(eco_id, updates, user_id)
        db.commit()
        return eco.to_dict()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_core_router.delete("/{eco_id}")
async def delete_eco(eco_id: str, db: Session = Depends(get_db)):
    """Delete an ECO (only in draft state)."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    if eco.state != ECOState.DRAFT.value:
        raise HTTPException(
            status_code=400, detail="Can only delete ECOs in draft state"
        )

    try:
        db.delete(eco)
        db.commit()
        return {"success": True, "message": "ECO deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_core_router.post("/{eco_id}/new-revision", response_model=Dict[str, Any])
async def create_new_revision(
    eco_id: str,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Create a new version/revision for the ECO's product.
    This creates a draft version that can be modified.
    """
    service = ECOService(db)
    try:
        version = service.action_new_revision(eco_id, user_id)
        db.commit()
        return {
            "success": True,
            "version_id": version.id,
            "version_label": version.version_label,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e
