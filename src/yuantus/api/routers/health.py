from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from fastapi import APIRouter
from sqlalchemy import text

from yuantus import __version__
from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.database import get_db_session
from yuantus.meta_engine.services.file_service import FileService
from yuantus.security.auth.database import get_identity_db_session

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    ctx = get_request_context()
    settings = get_settings()
    return {
        "ok": True,
        "service": "yuantus-plm",
        "version": __version__,
        "tenant_id": ctx.tenant_id,
        "org_id": ctx.org_id,
        "tenancy_mode": settings.TENANCY_MODE,
        "schema_mode": settings.SCHEMA_MODE,
        "audit_enabled": settings.AUDIT_ENABLED,
    }


def _check_external(url: str, timeout_s: int) -> dict:
    target = urljoin(url.rstrip("/") + "/", "health")
    req = Request(target, method="GET")
    try:
        with urlopen(req, timeout=timeout_s) as resp:  # nosec - health check only
            status = getattr(resp, "status", 200)
            return {"ok": 200 <= status < 300, "status": status, "url": target}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "url": target}


@router.get("/health/deps")
def health_deps() -> dict:
    ctx = get_request_context()
    settings = get_settings()
    deps: dict = {}
    overall_ok = True

    # Primary DB (tenant-scoped if configured)
    try:
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        deps["db"] = {"ok": True, "tenancy_mode": settings.TENANCY_MODE}
    except Exception as exc:
        deps["db"] = {"ok": False, "error": str(exc), "tenancy_mode": settings.TENANCY_MODE}
        overall_ok = False

    # Identity DB
    try:
        with get_identity_db_session() as db:
            db.execute(text("SELECT 1"))
        deps["identity_db"] = {"ok": True}
    except Exception as exc:
        deps["identity_db"] = {"ok": False, "error": str(exc)}
        overall_ok = False

    # Storage
    storage_info: dict = {"type": settings.STORAGE_TYPE}
    if settings.STORAGE_TYPE == "local":
        storage_path = Path(settings.LOCAL_STORAGE_PATH).resolve()
        writable = os.access(storage_path, os.W_OK)
        storage_info.update(
            {
                "path": str(storage_path),
                "exists": storage_path.exists(),
                "writable": writable,
                "ok": storage_path.exists() and writable,
            }
        )
        if not storage_info["ok"]:
            overall_ok = False
    else:
        probe_key = "healthcheck/ok.txt"
        file_service = FileService()
        try:
            exists = file_service.file_exists(probe_key)
            storage_info.update(
                {
                    "ok": True,
                    "bucket": settings.S3_BUCKET_NAME,
                    "endpoint_url": settings.S3_ENDPOINT_URL,
                    "probe_key": probe_key,
                    "exists": exists,
                }
            )
        except Exception as exc:
            storage_info.update(
                {
                    "ok": False,
                    "bucket": settings.S3_BUCKET_NAME,
                    "endpoint_url": settings.S3_ENDPOINT_URL,
                    "probe_key": probe_key,
                    "error": str(exc),
                }
            )
            overall_ok = False
    deps["storage"] = storage_info

    # External dependencies (optional)
    external_checks = {}
    configured = {
        "athena": settings.ATHENA_BASE_URL,
        "cad_ml": settings.CAD_ML_BASE_URL,
        "dedup_vision": settings.DEDUP_VISION_BASE_URL,
        "cad_extractor": settings.CAD_EXTRACTOR_BASE_URL,
    }
    if settings.HEALTHCHECK_EXTERNAL:
        timeout_s = max(int(settings.HEALTHCHECK_EXTERNAL_TIMEOUT_SECONDS or 2), 1)
        for name, url in configured.items():
            if not url:
                external_checks[name] = {"ok": None, "configured": False}
                continue
            result = _check_external(url, timeout_s)
            external_checks[name] = {"configured": True, **result}
            if result.get("ok") is False:
                overall_ok = False
    else:
        for name, url in configured.items():
            external_checks[name] = {"configured": bool(url), "checked": False}

    return {
        "ok": overall_ok,
        "service": "yuantus-plm",
        "version": __version__,
        "tenant_id": ctx.tenant_id,
        "org_id": ctx.org_id,
        "tenancy_mode": settings.TENANCY_MODE,
        "schema_mode": settings.SCHEMA_MODE,
        "deps": deps,
        "external": external_checks,
    }
