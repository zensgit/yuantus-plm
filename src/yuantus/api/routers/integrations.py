from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Dict, Optional

import httpx
from fastapi import APIRouter, Header

from yuantus.context import get_request_context
from yuantus.integrations.athena import AthenaClient
from yuantus.integrations.cad_ml import CadMLClient
from yuantus.integrations.dedup_vision import DedupVisionClient

router = APIRouter(prefix="/integrations", tags=["integrations"])


async def _probe(name: str, base_url: str, call: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        detail = await call
        return {"ok": True, "base_url": base_url, "detail": detail}
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "base_url": base_url,
            "status_code": exc.response.status_code,
            "error": exc.response.text,
        }
    except httpx.RequestError as exc:
        return {"ok": False, "base_url": base_url, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "base_url": base_url, "error": str(exc)}


@router.get("/health")
async def integrations_health(
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
            "athena",
            athena.base_url,
            athena.health(
                authorization=None, athena_authorization=athena_authorization
            ),
        ),
        "cad_ml": _probe("cad_ml", cad_ml.base_url, cad_ml.health(authorization=authorization)),
        "dedup_vision": _probe("dedup_vision", dedup.base_url, dedup.health(authorization=authorization)),
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
