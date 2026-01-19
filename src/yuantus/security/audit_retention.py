from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select

from yuantus.models.audit import AuditLog

_AUDIT_PRUNE_LOCK = threading.Lock()
_AUDIT_LAST_PRUNE_TS: dict[str, float] = {}


def _tenant_key(tenant_id: Optional[str]) -> str:
    return tenant_id or "__none__"


def get_last_prune_ts(tenant_id: Optional[str]) -> float:
    return _AUDIT_LAST_PRUNE_TS.get(_tenant_key(tenant_id), 0.0)


def mark_prune(tenant_id: Optional[str]) -> None:
    _AUDIT_LAST_PRUNE_TS[_tenant_key(tenant_id)] = time.time()


def _base_query(db, tenant_id: Optional[str]):
    query = db.query(AuditLog)
    if tenant_id is None:
        return query.filter(AuditLog.tenant_id.is_(None))
    return query.filter(AuditLog.tenant_id == tenant_id)


def prune_audit_logs(
    db,
    *,
    retention_days: int,
    retention_max_rows: int,
    tenant_id: Optional[str],
) -> int:
    deleted = 0

    if retention_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        deleted += (
            _base_query(db, tenant_id)
            .filter(AuditLog.created_at < cutoff)
            .delete(synchronize_session=False)
        )

    if retention_max_rows > 0:
        total = (
            _base_query(db, tenant_id)
            .with_entities(func.count(AuditLog.id))
            .scalar()
            or 0
        )
        if total > retention_max_rows:
            subq = (
                _base_query(db, tenant_id)
                .order_by(AuditLog.created_at.desc())
                .with_entities(AuditLog.id)
                .offset(retention_max_rows)
                .subquery()
            )
            deleted += (
                db.query(AuditLog)
                .filter(AuditLog.id.in_(select(subq.c.id)))
                .delete(synchronize_session=False)
            )

    if deleted:
        db.commit()

    return deleted


def maybe_prune_audit_logs(db, settings, tenant_id: Optional[str]) -> None:
    retention_days = int(settings.AUDIT_RETENTION_DAYS or 0)
    retention_max_rows = int(settings.AUDIT_RETENTION_MAX_ROWS or 0)
    if retention_days <= 0 and retention_max_rows <= 0:
        return

    interval = int(settings.AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS or 0)
    now_ts = time.time()
    last_ts = get_last_prune_ts(tenant_id)

    if interval > 0 and now_ts - last_ts < interval:
        return

    with _AUDIT_PRUNE_LOCK:
        last_ts = get_last_prune_ts(tenant_id)
        if interval > 0 and now_ts - last_ts < interval:
            return
        try:
            prune_audit_logs(
                db,
                retention_days=retention_days,
                retention_max_rows=retention_max_rows,
                tenant_id=tenant_id,
            )
        finally:
            mark_prune(tenant_id)
