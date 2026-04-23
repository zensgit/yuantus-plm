"""
ECO lifecycle router slice.

R6 of the ECO router decomposition owns lifecycle actions: cancel, suspend,
unsuspend, unsuspend diagnostics, and stage movement. CRUD and product binding
remain in the legacy ECO router.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import (
    CurrentUser,
    get_current_user_id,
    get_current_user_id_optional,
    get_current_user_optional,
)
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.services.eco_service import ECOService
from yuantus.meta_engine.web.release_diagnostics_models import (
    ReleaseDiagnosticsResponse,
    issue_to_response,
)

eco_lifecycle_router = APIRouter(prefix="/eco", tags=["ECO"])


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


@eco_lifecycle_router.post("/{eco_id}/cancel", response_model=Dict[str, Any])
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


@eco_lifecycle_router.get(
    "/{eco_id}/unsuspend-diagnostics", response_model=ReleaseDiagnosticsResponse
)
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


@eco_lifecycle_router.post("/{eco_id}/suspend", response_model=Dict[str, Any])
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


@eco_lifecycle_router.post("/{eco_id}/unsuspend", response_model=Dict[str, Any])
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


@eco_lifecycle_router.post("/{eco_id}/move-stage", response_model=Dict[str, Any])
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
