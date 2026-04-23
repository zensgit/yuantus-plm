"""
ECO (Engineering Change Order) Router
Sprint 3: Complete ECO Change Management System

API Endpoints:
- ECO CRUD operations
- Stage management
- Approval workflow
- BOM change tracking

IMPORTANT: Route order matters in FastAPI!
Specific routes (/kanban) must be defined
BEFORE parameterized routes (/{eco_id}) to ensure correct matching.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from yuantus.database import get_db
from yuantus.api.dependencies.auth import (
    CurrentUser,
    get_current_user_id,
    get_current_user_id_optional,
    get_current_user_optional,
)
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.services.eco_service import (
    ECOService,
    ECOStageService,
)
from yuantus.meta_engine.models.eco import ECOState
from yuantus.meta_engine.web.release_diagnostics_models import (
    ReleaseDiagnosticsResponse,
    issue_to_response,
)

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


class BindProductRequest(BaseModel):
    """Schema for binding a product to an ECO."""

    product_id: str = Field(..., min_length=1)
    create_target_revision: bool = Field(default=False)


class MoveStageRequest(BaseModel):
    """Schema for moving to a stage."""

    stage_id: str


class SuspendRequest(BaseModel):
    """Schema for suspend action."""

    reason: Optional[str] = None


class UnsuspendRequest(BaseModel):
    """Schema for unsuspend action."""

    resume_state: Optional[str] = None


def _ensure_can_unsuspend_eco(service: ECOService, *, eco_id: str, user_id: int) -> None:
    try:
        service.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="unsuspend"
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc


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
            "sla_hours": stage.sla_hours,
        }
        result["stages"].append(stage_data)

        # Get ECOs for this stage
        ecos = eco_service.list_ecos(stage_id=stage.id, product_id=product_id)
        result["ecos_by_stage"][stage.id] = [eco.to_dict() for eco in ecos]

    return result


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


@eco_router.post("/{eco_id}/bind-product", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=400, detail=str(e))


@eco_router.put("/{eco_id}", response_model=Dict[str, Any])
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


@eco_router.get("/{eco_id}/unsuspend-diagnostics", response_model=ReleaseDiagnosticsResponse)
async def get_eco_unsuspend_diagnostics(
    eco_id: str,
    resume_state: Optional[str] = Query(None),
    ruleset_id: str = Query("default"),
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> ReleaseDiagnosticsResponse:
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if eco:
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        _ensure_can_unsuspend_eco(service, eco_id=eco_id, user_id=user.id)

    diagnostics = service.get_unsuspend_diagnostics(
        eco_id,
        user.id if user is not None else 0,
        resume_state=resume_state,
        ruleset_id=ruleset_id,
    )
    errors = [issue_to_response(issue) for issue in (diagnostics.get("errors") or [])]
    warnings = [issue_to_response(issue) for issue in (diagnostics.get("warnings") or [])]
    return ReleaseDiagnosticsResponse(
        ok=len(errors) == 0,
        resource_type="eco",
        resource_id=eco_id,
        ruleset_id=str(diagnostics.get("ruleset_id") or ruleset_id),
        errors=errors,
        warnings=warnings,
    )


@eco_router.post("/{eco_id}/suspend", response_model=Dict[str, Any])
async def suspend_eco(
    eco_id: str,
    data: SuspendRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Suspend an ECO without canceling it."""
    service = ECOService(db)
    try:
        eco = service.action_suspend(eco_id, user_id, data.reason)
        db.commit()
        return eco.to_dict()
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@eco_router.post("/{eco_id}/unsuspend", response_model=Dict[str, Any])
async def unsuspend_eco(
    eco_id: str,
    data: UnsuspendRequest,
    force: bool = Query(False),
    ruleset_id: str = Query("default"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Unsuspend an ECO and resume it into a working state."""
    service = ECOService(db)
    try:
        if not force:
            eco = service.get_eco(eco_id)
            if eco:
                _ensure_can_unsuspend_eco(service, eco_id=eco_id, user_id=user_id)
            diagnostics = service.get_unsuspend_diagnostics(
                eco_id,
                user_id,
                resume_state=data.resume_state,
                ruleset_id=ruleset_id,
            )
            err_count = len(diagnostics.get("errors") or [])
            warn_count = len(diagnostics.get("warnings") or [])
            if err_count:
                resume_query = f"&resume_state={data.resume_state}" if data.resume_state else ""
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"ECO unsuspend blocked: errors={err_count}, warnings={warn_count}. "
                        f"Run /api/v1/eco/{eco_id}/unsuspend-diagnostics?ruleset_id={ruleset_id}{resume_query} for details."
                    ),
                )

        eco = service.action_unsuspend(
            eco_id,
            user_id,
            resume_state=data.resume_state,
        )
        db.commit()
        return eco.to_dict()
    except HTTPException:
        raise
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc
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
