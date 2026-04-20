from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, Header

from yuantus.api.dependencies.auth import get_current_user_id
from yuantus.context import get_request_context
from yuantus.integrations.athena import AthenaClient
from yuantus.integrations.cad_ml import CadMLClient
from yuantus.integrations.dedup_vision import DedupVisionClient

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _error_summary(error_code: str, *, status_code: Optional[int] = None, error_type: str) -> str:
    if error_code == "upstream_http_error":
        return f"upstream returned HTTP {status_code} ({error_type})"
    if error_code == "upstream_request_error":
        return f"upstream request failed ({error_type})"
    return f"upstream internal failure ({error_type})"


async def _probe(call: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        detail = await call
        return {"ok": True, "detail": detail}
    except httpx.HTTPStatusError as exc:
        error_code = "upstream_http_error"
        return {
            "ok": False,
            "error_code": error_code,
            "status_code": exc.response.status_code,
            "error_type": type(exc).__name__,
            "summary": _error_summary(
                error_code,
                status_code=exc.response.status_code,
                error_type=type(exc).__name__,
            ),
        }
    except httpx.RequestError as exc:
        error_code = "upstream_request_error"
        return {
            "ok": False,
            "error_code": error_code,
            "error_type": type(exc).__name__,
            "summary": _error_summary(error_code, error_type=type(exc).__name__),
        }
    except Exception as exc:  # pragma: no cover - defensive
        error_code = "upstream_internal_error"
        return {
            "ok": False,
            "error_code": error_code,
            "error_type": type(exc).__name__,
            "summary": _error_summary(error_code, error_type=type(exc).__name__),
        }


@router.get("/health")
async def integrations_health(
    _: int = Depends(get_current_user_id),
    authorization: Optional[str] = Header(default=None),
    athena_authorization: Optional[str] = Header(
        default=None, alias="X-Athena-Authorization"
    ),
) -> Dict[str, Any]:
    ctx = get_request_context()

    athena = AthenaClient()
    cad_ml = CadMLClient()
    dedup = DedupVisionClient()

    tasks = {
        "athena": _probe(
            athena.health(
                authorization=None, athena_authorization=athena_authorization
            ),
        ),
        "cad_ml": _probe(cad_ml.health(authorization=authorization)),
        "dedup_vision": _probe(dedup.health(authorization=authorization)),
    }

    results = await asyncio.gather(*tasks.values())
    services = dict(zip(tasks.keys(), results))

    overall_ok = all(v.get("ok") for v in services.values())
    return {
        "ok": overall_ok,
        "tenant_id": ctx.tenant_id,
        "org_id": ctx.org_id,
        "services": services,
    }
