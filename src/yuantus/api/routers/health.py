from __future__ import annotations

from fastapi import APIRouter

from yuantus import __version__
from yuantus.context import get_request_context

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    ctx = get_request_context()
    return {
        "ok": True,
        "service": "yuantus-plm",
        "version": __version__,
        "tenant_id": ctx.tenant_id,
        "org_id": ctx.org_id,
    }

