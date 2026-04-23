"""
ECO approval operations router.

Owns the approval dashboard and anomaly read/export endpoints split out of the
legacy ECO router. Write-path approval actions remain in `eco_router.py`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.services.eco_service import ECOApprovalService


eco_approval_ops_router = APIRouter(prefix="/eco", tags=["ECO"])


def _parse_deadline(value: Optional[str], param_name: str):
    """Parse ISO datetime string or raise 400."""
    if not value:
        return None
    from datetime import datetime as dt

    try:
        return dt.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name}: '{value}' is not a valid ISO datetime",
        )


@eco_approval_ops_router.get("/approvals/dashboard/summary", response_model=Dict[str, Any])
async def approval_dashboard_summary(
    company_id: Optional[str] = Query(None),
    eco_type: Optional[str] = Query(None, description="bom|routing|..."),
    eco_state: Optional[str] = Query(None, description="draft|progress"),
    deadline_from: Optional[str] = Query(None, description="ISO datetime"),
    deadline_to: Optional[str] = Query(None, description="ISO datetime"),
    db: Session = Depends(get_db),
):
    """Aggregate counts for approval operations dashboard."""
    dfrom = _parse_deadline(deadline_from, "deadline_from")
    dto = _parse_deadline(deadline_to, "deadline_to")
    service = ECOApprovalService(db)
    return service.get_approval_dashboard_summary(
        company_id=company_id,
        eco_type=eco_type,
        eco_state=eco_state,
        deadline_from=dfrom,
        deadline_to=dto,
    )


@eco_approval_ops_router.get("/approvals/dashboard/items", response_model=List[Dict[str, Any]])
async def approval_dashboard_items(
    status: Optional[str] = Query(None, description="overdue|pending|escalated"),
    stage_id: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    eco_type: Optional[str] = Query(None),
    eco_state: Optional[str] = Query(None),
    deadline_from: Optional[str] = Query(None, description="ISO datetime"),
    deadline_to: Optional[str] = Query(None, description="ISO datetime"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Filtered approval items for the operations dashboard."""
    dfrom = _parse_deadline(deadline_from, "deadline_from")
    dto = _parse_deadline(deadline_to, "deadline_to")
    service = ECOApprovalService(db)
    return service.get_approval_dashboard_items(
        status_filter=status,
        stage_id=stage_id,
        assignee_id=assignee_id,
        role=role,
        company_id=company_id,
        eco_type=eco_type,
        eco_state=eco_state,
        deadline_from=dfrom,
        deadline_to=dto,
        limit=limit,
    )


@eco_approval_ops_router.get("/approvals/dashboard/export")
async def approval_dashboard_export(
    fmt: str = Query("json", description="json|csv"),
    status: Optional[str] = Query(None, description="overdue|pending|escalated"),
    stage_id: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    eco_type: Optional[str] = Query(None),
    eco_state: Optional[str] = Query(None),
    deadline_from: Optional[str] = Query(None),
    deadline_to: Optional[str] = Query(None),
    limit: int = Query(1000, le=5000),
    db: Session = Depends(get_db),
):
    """Export dashboard items as JSON or CSV."""
    dfrom = _parse_deadline(deadline_from, "deadline_from")
    dto = _parse_deadline(deadline_to, "deadline_to")
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: '{fmt}'. Use 'json' or 'csv'.")
    service = ECOApprovalService(db)
    content = service.export_dashboard_items(
        fmt=fmt,
        status_filter=status,
        stage_id=stage_id,
        assignee_id=assignee_id,
        role=role,
        company_id=company_id,
        eco_type=eco_type,
        eco_state=eco_state,
        deadline_from=dfrom,
        deadline_to=dto,
        limit=limit,
    )
    media_type = "text/csv" if fmt == "csv" else "application/json"
    filename = f"approval_dashboard.{fmt}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@eco_approval_ops_router.get("/approvals/audit/anomalies", response_model=Dict[str, Any])
async def approval_anomalies(db: Session = Depends(get_db)):
    """Return no_candidates, escalated_unresolved, and overdue_not_escalated anomalies."""
    service = ECOApprovalService(db)
    return service.get_approval_anomalies()
