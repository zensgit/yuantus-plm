from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from yuantus.api.middleware.auth_enforce import _is_mes_ingest_path
from yuantus.config import get_settings
from yuantus.context import org_id_var, tenant_id_var


class TenantOrgContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        # The MES ingest route is a machine entrypoint whose tenant is bound by its
        # dedicated credential (api/dependencies/mes_ingest_auth), NOT the request
        # header. Do NOT derive tenant/org from the untrusted x-tenant-id header for
        # it -- otherwise the audit log (which reads tenant_id_var) would record a
        # caller-supplied tenant for that path. Data isolation is unaffected (the
        # credential pins the bound tenant on its own session).
        if _is_mes_ingest_path(request.url.path):
            tenant_id = None
            org_id = None
        else:
            tenant_id = request.headers.get(settings.TENANT_HEADER)
            org_id = request.headers.get(settings.ORG_HEADER)

        tenant_token = None
        org_token = None

        # Respect any upstream middleware (e.g. auth enforcement) that already
        # established request-scoped tenant/org context.
        if tenant_id_var.get() is None:
            tenant_token = tenant_id_var.set(tenant_id)
            request.state.tenant_id = tenant_id
        if org_id_var.get() is None:
            org_token = org_id_var.set(org_id)
            request.state.org_id = org_id
        try:
            return await call_next(request)
        finally:
            if tenant_token is not None:
                tenant_id_var.reset(tenant_token)
            if org_token is not None:
                org_id_var.reset(org_token)
