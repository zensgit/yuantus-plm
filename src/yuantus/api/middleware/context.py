from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from yuantus.config import get_settings
from yuantus.context import org_id_var, tenant_id_var


class TenantOrgContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        tenant_id = request.headers.get(settings.TENANT_HEADER)
        org_id = request.headers.get(settings.ORG_HEADER)

        tenant_token = None
        org_token = None

        # Respect any upstream middleware (e.g. auth enforcement) that already
        # established request-scoped tenant/org context.
        if tenant_id_var.get() is None:
            tenant_token = tenant_id_var.set(tenant_id)
        if org_id_var.get() is None:
            org_token = org_id_var.set(org_id)
        try:
            return await call_next(request)
        finally:
            if tenant_token is not None:
                tenant_id_var.reset(tenant_token)
            if org_token is not None:
                org_id_var.reset(org_token)
