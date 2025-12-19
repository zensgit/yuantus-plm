"""
ECO (Engineering Change Order) Router
Sprint 3: Complete ECO Change Management System

API Endpoints:
- ECO CRUD operations
- Stage management
- Approval workflow
- BOM change tracking

IMPORTANT: Route order matters in FastAPI!
Specific routes (/kanban, /stages, /approvals/pending) must be defined
BEFORE parameterized routes (/{eco_id}) to ensure correct matching.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.services.eco_service import (
    ECOService,
    ECOApprovalService,
    ECOStageService,
)
from yuantus.meta_engine.models.eco import ECOState

eco_router = APIRouter(prefix="/eco", tags=["ECO"])


# ============ Pydantic Schemas ============


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


class MoveStageRequest(BaseModel):
    """Schema for moving to a stage."""

    stage_id: str


class ApprovalRequest(BaseModel):
    """Schema for approval actions."""

    comment: Optional[str] = None


class RejectRequest(BaseModel):
    """Schema for rejection."""

    comment: str = Field(..., min_length=1)


class StageCreate(BaseModel):
    """Schema for creating a stage."""

    name: str = Field(..., min_length=1, max_length=100)
    sequence: Optional[int] = None
    approval_type: str = Field(default="none")
    approval_roles: Optional[List[str]] = None
    is_blocking: bool = False
    auto_progress: bool = False
    description: Optional[str] = None


class StageUpdate(BaseModel):
    """Schema for updating a stage."""

    name: Optional[str] = None
    sequence: Optional[int] = None
    approval_type: Optional[str] = None
    approval_roles: Optional[List[str]] = None
    is_blocking: Optional[bool] = None
    auto_progress: Optional[bool] = None
    description: Optional[str] = None


# ============================================================
# SPECIFIC ROUTES (must be defined BEFORE /{eco_id} routes)
# ============================================================

# ============ Kanban View Endpoint ============


@eco_router.get("/kanban", response_model=Dict[str, Any])
async def get_kanban_view(
    product_id: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Get ECOs organized by stage for Kanban view.

    Returns:
        Dict with stages as keys and ECO lists as values
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
        }
        result["stages"].append(stage_data)

        # Get ECOs for this stage
        ecos = eco_service.list_ecos(stage_id=stage.id, product_id=product_id)
        result["ecos_by_stage"][stage.id] = [eco.to_dict() for eco in ecos]

    return result


# ============ Stage Endpoints ============


@eco_router.get("/stages", response_model=List[Dict[str, Any]])
async def list_stages(db: Session = Depends(get_db)):
    """List all ECO stages."""
    service = ECOStageService(db)
    stages = service.list_stages()
    return [
        {
            "id": s.id,
            "name": s.name,
            "sequence": s.sequence,
            "approval_type": s.approval_type,
            "approval_roles": s.approval_roles,
            "is_blocking": s.is_blocking,
            "auto_progress": s.auto_progress,
            "fold": s.fold,
            "description": s.description,
        }
        for s in stages
    ]


@eco_router.post("/stages", response_model=Dict[str, Any])
async def create_stage(data: StageCreate, db: Session = Depends(get_db)):
    """Create a new ECO stage."""
    service = ECOStageService(db)
    try:
        stage = service.create_stage(
            name=data.name,
            sequence=data.sequence,
            approval_type=data.approval_type,
            approval_roles=data.approval_roles,
            is_blocking=data.is_blocking,
            auto_progress=data.auto_progress,
            description=data.description,
        )
        db.commit()
        return {
            "id": stage.id,
            "name": stage.name,
            "sequence": stage.sequence,
            "approval_type": stage.approval_type,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@eco_router.put("/stages/{stage_id}", response_model=Dict[str, Any])
async def update_stage(stage_id: str, data: StageUpdate, db: Session = Depends(get_db)):
    """Update an ECO stage."""
    service = ECOStageService(db)
    try:
        update_data = data.dict(exclude_unset=True)
        stage = service.update_stage(stage_id, **update_data)
        db.commit()
        return {
            "id": stage.id,
            "name": stage.name,
            "sequence": stage.sequence,
            "approval_type": stage.approval_type,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@eco_router.delete("/stages/{stage_id}")
async def delete_stage(stage_id: str, db: Session = Depends(get_db)):
    """Delete an ECO stage."""
    service = ECOStageService(db)
    try:
        success = service.delete_stage(stage_id)
        if not success:
            raise HTTPException(status_code=404, detail="Stage not found")
        db.commit()
        return {"success": True, "message": "Stage deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============ Pending Approvals (specific route) ============


@eco_router.get("/approvals/pending", response_model=List[Dict[str, Any]])
async def get_pending_approvals(
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Get all pending approvals for a user."""
    service = ECOApprovalService(db)
    return service.get_pending_approvals(user_id)


# ============================================================
# ECO CRUD Endpoints (includes /{eco_id} routes)
# ============================================================


@eco_router.post("", response_model=Dict[str, Any])
async def create_eco(
    data: ECOCreate,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Create a new ECO.

    Args:
        data: ECO creation data
        user_id: User creating the ECO

    Returns:
        Created ECO data
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
        raise HTTPException(status_code=400, detail=str(e))


@eco_router.get("", response_model=List[Dict[str, Any]])
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
        state: Filter by state (draft, progress, approved, done, canceled)
        stage_id: Filter by stage
        product_id: Filter by product
        created_by_id: Filter by creator
        limit: Max results
        offset: Pagination offset

    Returns:
        List of ECOs
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


@eco_router.get("/{eco_id}", response_model=Dict[str, Any])
async def get_eco(eco_id: str, db: Session = Depends(get_db)):
    """Get ECO by ID."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")
    return eco.to_dict()


@eco_router.put("/{eco_id}", response_model=Dict[str, Any])
async def update_eco(eco_id: str, data: ECOUpdate, db: Session = Depends(get_db)):
    """Update an ECO."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    # Only allow updates in draft/progress state
    if eco.state not in (ECOState.DRAFT.value, ECOState.PROGRESS.value):
        raise HTTPException(
            status_code=400, detail=f"Cannot update ECO in {eco.state} state"
        )

    try:
        if data.name is not None:
            eco.name = data.name
        if data.description is not None:
            eco.description = data.description
        if data.priority is not None:
            eco.priority = data.priority
        if data.effectivity_date is not None:
            eco.effectivity_date = data.effectivity_date

        eco.updated_at = datetime.utcnow()
        db.commit()
        return eco.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@eco_router.delete("/{eco_id}")
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
        raise HTTPException(status_code=400, detail=str(e))


# ============ ECO Actions Endpoints ============


@eco_router.post("/{eco_id}/new-revision", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.post("/{eco_id}/apply", response_model=Dict[str, Any])
async def apply_eco(
    eco_id: str,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Apply the ECO changes.
    Sets the target version as current and marks ECO as done.
    """
    service = ECOService(db)
    try:
        success = service.action_apply(eco_id, user_id)
        db.commit()
        return {"success": success, "message": "ECO applied successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.post("/{eco_id}/cancel", response_model=Dict[str, Any])
async def cancel_eco(
    eco_id: str,
    reason: Optional[str] = None,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Cancel an ECO."""
    service = ECOService(db)
    try:
        eco = service.action_cancel(eco_id, user_id, reason)
        db.commit()
        return eco.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.post("/{eco_id}/move-stage", response_model=Dict[str, Any])
async def move_to_stage(
    eco_id: str,
    data: MoveStageRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Move ECO to a different stage."""
    service = ECOService(db)
    try:
        eco = service.move_to_stage(eco_id, data.stage_id, user_id)
        db.commit()
        return eco.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============ BOM Changes Endpoints ============


@eco_router.get("/{eco_id}/changes", response_model=List[Dict[str, Any]])
async def get_bom_changes(eco_id: str, db: Session = Depends(get_db)):
    """Get all BOM changes for an ECO."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    changes = service.get_bom_changes(eco_id)
    return [c.to_dict() for c in changes]


@eco_router.post("/{eco_id}/compute-changes", response_model=List[Dict[str, Any]])
async def compute_bom_changes(eco_id: str, db: Session = Depends(get_db)):
    """
    Compute BOM differences between source and target versions.
    Creates/updates ECOBOMChange records.
    """
    service = ECOService(db)
    try:
        changes = service.compute_bom_changes(eco_id)
        db.commit()
        return [c.to_dict() for c in changes]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.get("/{eco_id}/conflicts", response_model=List[Dict[str, Any]])
async def detect_conflicts(eco_id: str, db: Session = Depends(get_db)):
    """
    Detect rebase conflicts for an ECO.
    Compares Base (source) vs Mine (target) vs Theirs (current product version).
    """
    service = ECOService(db)
    try:
        conflicts = service.detect_rebase_conflicts(eco_id)
        return conflicts
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Approval Endpoints ============


@eco_router.post("/{eco_id}/approve", response_model=Dict[str, Any])
async def approve_eco(
    eco_id: str,
    data: ApprovalRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Approve an ECO at its current stage."""
    service = ECOApprovalService(db)
    try:
        approval = service.approve(eco_id, user_id, data.comment)
        db.commit()
        return approval.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.post("/{eco_id}/reject", response_model=Dict[str, Any])
async def reject_eco(
    eco_id: str,
    data: RejectRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Reject an ECO at its current stage."""
    service = ECOApprovalService(db)
    try:
        approval = service.reject(eco_id, user_id, data.comment)
        db.commit()
        return approval.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.get("/{eco_id}/approvals", response_model=List[Dict[str, Any]])
async def get_eco_approvals(eco_id: str, db: Session = Depends(get_db)):
    """Get all approval records for an ECO."""
    service = ECOApprovalService(db)
    approvals = service.get_eco_approvals(eco_id)
    return [a.to_dict() for a in approvals]
