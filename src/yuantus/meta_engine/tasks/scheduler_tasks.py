from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.meta_engine.services.eco_service import ECOApprovalService
from yuantus.security.audit_retention import mark_prune, prune_audit_logs


def eco_approval_escalation(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    user_id = int(payload.get("user_id") or get_settings().SCHEDULER_SYSTEM_USER_ID or 1)
    result = ECOApprovalService(session).escalate_overdue_approvals(user_id=user_id)
    return {"ok": True, "task": "eco_approval_escalation", **result}


def audit_retention_prune(payload: Dict[str, Any], session: Session) -> Dict[str, Any]:
    settings = get_settings()
    tenant_id = payload.get("tenant_id")
    retention_days = int(settings.AUDIT_RETENTION_DAYS or 0)
    retention_max_rows = int(settings.AUDIT_RETENTION_MAX_ROWS or 0)
    if retention_days <= 0 and retention_max_rows <= 0:
        return {
            "ok": True,
            "task": "audit_retention_prune",
            "skipped": True,
            "reason": "retention_disabled",
            "deleted": 0,
            "tenant_id": tenant_id,
        }

    deleted = prune_audit_logs(
        session,
        retention_days=retention_days,
        retention_max_rows=retention_max_rows,
        tenant_id=tenant_id,
    )
    mark_prune(tenant_id)
    return {
        "ok": True,
        "task": "audit_retention_prune",
        "deleted": deleted,
        "tenant_id": tenant_id,
        "retention_days": retention_days,
        "retention_max_rows": retention_max_rows,
    }
