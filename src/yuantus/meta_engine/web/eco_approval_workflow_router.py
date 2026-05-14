"""
ECO approval workflow router.

Owns approval workflow read/write endpoints split out of the legacy ECO
router. Dashboard/audit ops endpoints remain in `eco_approval_ops_router.py`,
while ECO lifecycle routes remain in `eco_router.py`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import (
    get_current_user_id,
    get_current_user_id_optional,
)
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.services.audit_service import AuditService
from yuantus.meta_engine.services.eco_service import ECOApprovalService
from yuantus.meta_engine.services.notification_service import NotificationService


eco_approval_workflow_router = APIRouter(prefix="/eco", tags=["ECO"])


class ApprovalRequest(BaseModel):
    """Schema for approval actions."""

    comment: Optional[str] = None


class RejectRequest(BaseModel):
    """Schema for rejection."""

    comment: str = Field(..., min_length=1)


class BatchApprovalRequest(BaseModel):
    """Batch approval schema."""

    eco_ids: List[str] = Field(..., min_length=1)
    mode: str = Field(..., description="approve|reject")
    comment: Optional[str] = None


@eco_approval_workflow_router.get("/approvals/pending", response_model=List[Dict[str, Any]])
async def get_pending_approvals(
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Get all pending approvals for a user."""
    service = ECOApprovalService(db)
    return service.get_pending_approvals(user_id)


@eco_approval_workflow_router.post("/approvals/batch", response_model=Dict[str, Any])
async def batch_approvals(
    data: BatchApprovalRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Batch approve/reject ECOs."""
    mode = data.mode.strip().lower()
    if mode not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="mode must be approve|reject")
    if mode == "reject" and not data.comment:
        raise HTTPException(status_code=400, detail="comment required for reject")

    service = ECOApprovalService(db)
    audit_service = AuditService(db)
    notification_service = NotificationService(db)
    results: List[Dict[str, Any]] = []
    for eco_id in data.eco_ids:
        try:
            if mode == "approve":
                approval = service.approve(eco_id, user_id, data.comment)
            else:
                approval = service.reject(eco_id, user_id, data.comment)
            db.commit()
            results.append(
                {
                    "eco_id": eco_id,
                    "ok": True,
                    "approval_id": approval.id,
                    "status": approval.status,
                }
            )
        except Exception as e:
            db.rollback()
            results.append({"eco_id": eco_id, "ok": False, "error": str(e)})

    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    audit_service.log_action(
        str(user_id),
        f"eco.batch_{mode}",
        "ECO",
        "batch",
        details={
            "eco_ids": data.eco_ids,
            "ok": ok_count,
            "failed": fail_count,
        },
    )
    notification_service.notify(
        f"eco.batch_{mode}",
        {
            "eco_ids": data.eco_ids,
            "ok": ok_count,
            "failed": fail_count,
            "mode": mode,
        },
    )

    return {
        "mode": mode,
        "count": len(results),
        "summary": {"ok": ok_count, "failed": fail_count},
        "results": results,
    }


@eco_approval_workflow_router.get("/approvals/overdue", response_model=List[Dict[str, Any]])
async def list_overdue_approvals(db: Session = Depends(get_db)):
    """List overdue ECO approvals based on approval_deadline."""
    service = ECOApprovalService(db)
    return service.list_overdue_approvals()


@eco_approval_workflow_router.post("/approvals/notify-overdue", response_model=Dict[str, Any])
async def notify_overdue_approvals(db: Session = Depends(get_db)):
    """Send notifications for overdue ECO approvals."""
    service = ECOApprovalService(db)
    return service.notify_overdue_approvals()


@eco_approval_workflow_router.get("/{eco_id}/approval-routing", response_model=Dict[str, Any])
async def get_eco_approval_routing(
    eco_id: str,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Return the effective approval routing summary for the ECO's current stage."""
    service = ECOApprovalService(db)
    try:
        service.permission_service.check_permission(
            user_id, "read", "ECO", resource_id=eco_id
        )
        return service.get_approval_routing(eco_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=404 if "not found" in detail.lower() else 400,
            detail=detail,
        ) from exc


@eco_approval_workflow_router.post("/{eco_id}/auto-assign-approvers", response_model=Dict[str, Any])
async def auto_assign_approvers(
    eco_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """P2-2a: Auto-assign approvers for the current stage based on approval_roles.

    Auth: get_current_user_id (401 on no user).
    Permission: RBACUser.has_permission("eco.auto_assign") (403 on deny).
    """
    service = ECOApprovalService(db)
    try:
        result = service.auto_assign_stage_approvers(eco_id, user_id)
        db.commit()
        return result
    except PermissionError:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden: insufficient ECO permission")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_approval_workflow_router.post("/approvals/escalate-overdue", response_model=Dict[str, Any])
async def escalate_overdue_approvals(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """P2-2b: Escalate overdue pending approvals to admin/superuser.

    Auth: get_current_user_id (401 on no user).
    Permission: RBACUser.has_permission("eco.escalate_overdue") (403 on deny).
    """
    service = ECOApprovalService(db)
    try:
        result = service.escalate_overdue_approvals(user_id)
        db.commit()
        return result
    except PermissionError:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden: insufficient ECO permission")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_approval_workflow_router.post("/{eco_id}/approve", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_approval_workflow_router.post("/{eco_id}/reject", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_approval_workflow_router.get("/{eco_id}/approvals", response_model=List[Dict[str, Any]])
async def get_eco_approvals(eco_id: str, db: Session = Depends(get_db)):
    """Get all approval records for an ECO."""
    service = ECOApprovalService(db)
    approvals = service.get_eco_approvals(eco_id)
    return [a.to_dict() for a in approvals]
