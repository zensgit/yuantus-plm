from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from yuantus.config import get_settings
from yuantus.context import get_request_context, user_id_var
from yuantus.models.audit import AuditLog
from yuantus.security.auth.database import get_identity_sessionmaker

_AUDIT_PRUNE_LOCK = threading.Lock()
_AUDIT_LAST_PRUNE_TS = 0.0


def _prune_audit_logs(
    db, *, retention_days: int, retention_max_rows: int
) -> None:
    deleted = 0
    if retention_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        deleted += (
            db.query(AuditLog)
            .filter(AuditLog.created_at < cutoff)
            .delete(synchronize_session=False)
        )

    if retention_max_rows > 0:
        total = db.query(func.count(AuditLog.id)).scalar() or 0
        if total > retention_max_rows:
            subq = (
                db.query(AuditLog.id)
                .order_by(AuditLog.created_at.desc())
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


def _maybe_prune_audit_logs(db, settings) -> None:
    global _AUDIT_LAST_PRUNE_TS
    retention_days = int(settings.AUDIT_RETENTION_DAYS or 0)
    retention_max_rows = int(settings.AUDIT_RETENTION_MAX_ROWS or 0)
    if retention_days <= 0 and retention_max_rows <= 0:
        return

    interval = int(settings.AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS or 0)
    now_ts = time.time()
    if interval > 0 and now_ts - _AUDIT_LAST_PRUNE_TS < interval:
        return

    with _AUDIT_PRUNE_LOCK:
        if interval > 0 and now_ts - _AUDIT_LAST_PRUNE_TS < interval:
            return
        try:
            _prune_audit_logs(
                db,
                retention_days=retention_days,
                retention_max_rows=retention_max_rows,
            )
        finally:
            _AUDIT_LAST_PRUNE_TS = time.time()


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not settings.AUDIT_ENABLED:
            return await call_next(request)

        start = time.perf_counter()
        error: Optional[str] = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            try:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                ctx = get_request_context()
                uid_raw = user_id_var.get()
                user_id = int(uid_raw) if uid_raw and str(uid_raw).isdigit() else None

                client_ip = None
                if request.client:
                    client_ip = request.client.host

                SessionLocal = get_identity_sessionmaker()
                db = SessionLocal()
                try:
                    db.add(
                        AuditLog(
                            tenant_id=ctx.tenant_id,
                            org_id=ctx.org_id,
                            user_id=user_id,
                            method=request.method,
                            path=request.url.path,
                            status_code=status_code,
                            duration_ms=elapsed_ms,
                            client_ip=client_ip,
                            user_agent=request.headers.get("user-agent"),
                            error=error,
                        )
                    )
                    db.commit()
                    _maybe_prune_audit_logs(db, settings)
                finally:
                    db.close()
            except Exception:
                # Never break the main request flow because of audit logging.
                pass
