from __future__ import annotations

import time
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from yuantus.config import get_settings
from yuantus.context import get_request_context, user_id_var
from yuantus.models.audit import AuditLog
from yuantus.security.audit_retention import maybe_prune_audit_logs
from yuantus.security.auth.database import get_identity_sessionmaker


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
                    maybe_prune_audit_logs(db, settings, ctx.tenant_id)
                finally:
                    db.close()
            except Exception:
                # Never break the main request flow because of audit logging.
                pass
