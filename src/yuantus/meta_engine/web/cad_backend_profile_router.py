from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import (
    CurrentUser,
    get_current_user,
    require_admin_user,
)
from yuantus.config import (
    available_cad_step_iges_backends,
    cad_connector_base_url_configured,
    configured_cad_step_iges_backend_name,
    effective_cad_step_iges_backend,
    get_settings,
    normalize_cad_connector_mode,
)
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.integrations.cad_connectors import registry as cad_registry
from yuantus.meta_engine.services.cad_backend_profile_service import (
    CadBackendProfileResolution,
    CadBackendProfileService,
)

cad_backend_profile_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadConnectorInfoResponse(BaseModel):
    id: str
    label: str
    cad_format: Optional[str] = None
    document_type: Optional[str] = None
    extensions: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    priority: int = 100
    description: Optional[str] = None


class CadCapabilityMode(BaseModel):
    available: bool
    modes: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    status: str = "ok"
    degraded_reason: Optional[str] = None


class CadCapabilitiesResponse(BaseModel):
    connectors: List[CadConnectorInfoResponse]
    counts: Dict[str, int]
    formats: Dict[str, List[str]]
    extensions: Dict[str, List[str]]
    features: Dict[str, CadCapabilityMode]
    integrations: Dict[str, Any]


class CadBackendProfileResponse(BaseModel):
    configured: str
    effective: str
    source: str
    options: List[str] = Field(default_factory=list)
    scope: Dict[str, Optional[str]]


class CadBackendProfileUpdateRequest(BaseModel):
    profile: str
    scope: str = Field(default="org", description="org|tenant")


def _feature_status(
    *,
    available: bool,
    modes: List[str],
    has_local_fallback: bool,
    remote_modes: Optional[List[str]] = None,
    disabled_reason: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    if not available:
        return {
            "status": "disabled",
            "degraded_reason": disabled_reason,
        }
    remote_set = set(remote_modes or [])
    if any(mode in remote_set for mode in modes):
        return {
            "status": "ok",
            "degraded_reason": None,
        }
    if has_local_fallback:
        return {
            "status": "degraded",
            "degraded_reason": "local fallback only",
        }
    return {
        "status": "ok",
        "degraded_reason": None,
    }


def _integration_status(
    *,
    configured: bool,
    available: bool,
    fallback_reason: Optional[str],
    disabled_reason: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    if configured and available:
        return {
            "status": "ok",
            "degraded_reason": None,
        }
    if not configured and fallback_reason:
        return {
            "status": "degraded",
            "degraded_reason": fallback_reason,
        }
    if not available:
        return {
            "status": "disabled",
            "degraded_reason": disabled_reason,
        }
    return {"status": "disabled", "degraded_reason": disabled_reason}


def _resolve_cad_backend_profile_response(db: Session) -> CadBackendProfileResolution:
    ctx = get_request_context()
    return CadBackendProfileService(db, get_settings()).resolve(
        tenant_id=ctx.tenant_id,
        org_id=ctx.org_id,
    )


@cad_backend_profile_router.get(
    "/backend-profile", response_model=CadBackendProfileResponse
)
def get_cad_backend_profile(
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
) -> CadBackendProfileResponse:
    resolution = _resolve_cad_backend_profile_response(db)
    return CadBackendProfileResponse(
        configured=resolution.configured,
        effective=resolution.effective,
        source=resolution.source,
        options=list(resolution.options),
        scope=dict(resolution.scope),
    )


@cad_backend_profile_router.put(
    "/backend-profile", response_model=CadBackendProfileResponse
)
def update_cad_backend_profile(
    payload: CadBackendProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_user),
) -> CadBackendProfileResponse:
    ctx = get_request_context()
    try:
        resolution = CadBackendProfileService(db, get_settings()).update_override(
            tenant_id=ctx.tenant_id,
            org_id=ctx.org_id,
            user_id=getattr(current_user, "id", None),
            profile=payload.profile,
            scope=payload.scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CadBackendProfileResponse(
        configured=resolution.configured,
        effective=resolution.effective,
        source=resolution.source,
        options=list(resolution.options),
        scope=dict(resolution.scope),
    )


@cad_backend_profile_router.delete(
    "/backend-profile", response_model=CadBackendProfileResponse
)
def delete_cad_backend_profile(
    scope: str = Query("org", description="org|tenant"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin_user),
) -> CadBackendProfileResponse:
    ctx = get_request_context()
    try:
        resolution = CadBackendProfileService(db, get_settings()).delete_override(
            tenant_id=ctx.tenant_id,
            org_id=ctx.org_id,
            scope=scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CadBackendProfileResponse(
        configured=resolution.configured,
        effective=resolution.effective,
        source=resolution.source,
        options=list(resolution.options),
        scope=dict(resolution.scope),
    )


@cad_backend_profile_router.get("/capabilities", response_model=CadCapabilitiesResponse)
def get_cad_capabilities(db: Session = Depends(get_db)) -> CadCapabilitiesResponse:
    settings = get_settings()
    connectors = sorted(cad_registry.list(), key=lambda info: info.id)

    def _collect(values):
        return sorted({v for v in values if v})

    formats_2d = _collect(
        info.cad_format for info in connectors if info.document_type == "2d"
    )
    formats_3d = _collect(
        info.cad_format for info in connectors if info.document_type == "3d"
    )
    extensions_2d = _collect(
        ext
        for info in connectors
        if info.document_type == "2d"
        for ext in info.extensions
    )
    extensions_3d = _collect(
        ext
        for info in connectors
        if info.document_type == "3d"
        for ext in info.extensions
    )

    resolution = _resolve_cad_backend_profile_response(db)
    cad_connector_mode = normalize_cad_connector_mode(settings.CAD_CONNECTOR_MODE)
    cad_connector_enabled = (
        resolution.effective != "local-baseline"
        and cad_connector_base_url_configured(settings)
    )
    cad_backend_profile = {
        "configured": resolution.configured,
        "effective": resolution.effective,
        "source": resolution.source,
        "options": list(resolution.options),
    }
    cad_step_iges_backend = {
        "configured": configured_cad_step_iges_backend_name(settings),
        "effective": effective_cad_step_iges_backend(
            settings,
            effective_profile=resolution.effective,
        ),
        "options": available_cad_step_iges_backends(),
        "formats": ["STEP", "IGES"],
        "extensions": ["step", "stp", "iges", "igs"],
    }
    cad_connector_disabled_reason = "CAD connector service not configured"
    if cad_connector_base_url_configured(settings) and not cad_connector_enabled:
        cad_connector_disabled_reason = (
            f"CAD backend profile {cad_backend_profile['effective']} selected"
        )
    cad_extractor_enabled = bool(settings.CAD_EXTRACTOR_BASE_URL)
    cad_ml_enabled = bool(settings.CAD_ML_BASE_URL)
    cadgf_enabled = bool(settings.CADGF_ROUTER_BASE_URL)

    preview_modes = ["local"]
    if cad_ml_enabled:
        preview_modes.append("cad_ml")
    if cad_connector_enabled:
        preview_modes.append("connector")

    geometry_modes = ["local"]
    if cad_connector_enabled:
        geometry_modes.append("connector")
    if cadgf_enabled:
        geometry_modes.append("cadgf")

    extract_modes = ["local"]
    if cad_extractor_enabled:
        extract_modes.append("extractor")
    if cad_connector_enabled:
        extract_modes.append("connector")

    features = {
        "preview": CadCapabilityMode(
            available=True,
            modes=preview_modes,
            **_feature_status(
                available=True,
                modes=preview_modes,
                has_local_fallback=True,
                remote_modes=["cad_ml", "connector"],
            ),
        ),
        "geometry": CadCapabilityMode(
            available=True,
            modes=geometry_modes,
            **_feature_status(
                available=True,
                modes=geometry_modes,
                has_local_fallback=True,
                remote_modes=["connector", "cadgf"],
            ),
        ),
        "extract": CadCapabilityMode(
            available=True,
            modes=extract_modes,
            **_feature_status(
                available=True,
                modes=extract_modes,
                has_local_fallback=True,
                remote_modes=["extractor", "connector"],
            ),
        ),
        "bom": CadCapabilityMode(
            available=cad_connector_enabled,
            modes=["connector"] if cad_connector_enabled else [],
            note="Requires CAD connector service",
            **_feature_status(
                available=cad_connector_enabled,
                modes=["connector"] if cad_connector_enabled else [],
                has_local_fallback=False,
                remote_modes=["connector"],
                disabled_reason="CAD connector service not configured",
            ),
        ),
        "manifest": CadCapabilityMode(
            available=cadgf_enabled,
            modes=["cadgf"] if cadgf_enabled else [],
            note="CADGF router produces manifest/document/metadata",
            **_feature_status(
                available=cadgf_enabled,
                modes=["cadgf"] if cadgf_enabled else [],
                has_local_fallback=False,
                remote_modes=["cadgf"],
                disabled_reason="CADGF router not configured",
            ),
        ),
        "metadata": CadCapabilityMode(
            available=True,
            modes=["extract", "cadgf"] if cadgf_enabled else ["extract"],
            **_feature_status(
                available=True,
                modes=["extract", "cadgf"] if cadgf_enabled else ["extract"],
                has_local_fallback=True,
                remote_modes=["cadgf"],
            ),
        ),
    }

    return CadCapabilitiesResponse(
        connectors=[
            CadConnectorInfoResponse(
                id=info.id,
                label=info.label,
                cad_format=info.cad_format,
                document_type=info.document_type,
                extensions=list(info.extensions),
                aliases=list(info.aliases),
                priority=info.priority,
                description=info.description,
            )
            for info in connectors
        ],
        counts={
            "total": len(connectors),
            "2d": len([c for c in connectors if c.document_type == "2d"]),
            "3d": len([c for c in connectors if c.document_type == "3d"]),
        },
        formats={"2d": formats_2d, "3d": formats_3d},
        extensions={"2d": extensions_2d, "3d": extensions_3d},
        features=features,
        integrations={
            "cad_connector": {
                "configured": cad_connector_base_url_configured(settings),
                "enabled": cad_connector_enabled,
                "mode": cad_connector_mode,
                "profile": cad_backend_profile,
                "step_iges_backend": cad_step_iges_backend,
                "base_url": settings.CAD_CONNECTOR_BASE_URL or None,
                **_integration_status(
                    configured=cad_connector_base_url_configured(settings),
                    available=cad_connector_enabled,
                    fallback_reason="local fallback only"
                    if not cad_connector_enabled
                    else None,
                    disabled_reason=cad_connector_disabled_reason,
                ),
            },
            "cad_extractor": {
                "configured": cad_extractor_enabled,
                "mode": settings.CAD_EXTRACTOR_MODE,
                "base_url": settings.CAD_EXTRACTOR_BASE_URL or None,
                **_integration_status(
                    configured=cad_extractor_enabled,
                    available=cad_extractor_enabled,
                    fallback_reason="local fallback only"
                    if not cad_extractor_enabled
                    else None,
                    disabled_reason="CAD extractor not configured",
                ),
            },
            "cad_ml": {
                "configured": cad_ml_enabled,
                "base_url": settings.CAD_ML_BASE_URL or None,
                **_integration_status(
                    configured=cad_ml_enabled,
                    available=cad_ml_enabled,
                    fallback_reason="local fallback only"
                    if not cad_ml_enabled
                    else None,
                    disabled_reason="CAD ML service not configured",
                ),
            },
            "cadgf_router": {
                "configured": cadgf_enabled,
                "base_url": settings.CADGF_ROUTER_BASE_URL or None,
                **_integration_status(
                    configured=cadgf_enabled,
                    available=cadgf_enabled,
                    fallback_reason=None,
                    disabled_reason="CADGF router not configured",
                ),
            },
        },
    )
