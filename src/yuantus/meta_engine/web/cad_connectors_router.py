from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from yuantus.api.dependencies.auth import CurrentUser, require_admin_user
from yuantus.config import get_settings
from yuantus.integrations.cad_connectors import (
    registry as cad_registry,
    reload_connectors,
)

cad_connectors_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadConnectorInfoResponse(BaseModel):
    id: str
    label: str
    cad_format: str
    document_type: str
    extensions: List[str]
    aliases: List[str] = Field(default_factory=list)
    priority: int
    description: Optional[str] = None


class CadConnectorReloadRequest(BaseModel):
    config_path: Optional[str] = None
    config: Optional[Any] = None


class CadConnectorReloadResponse(BaseModel):
    config_path: Optional[str] = None
    custom_loaded: int
    errors: List[str] = Field(default_factory=list)


@cad_connectors_router.get("/connectors", response_model=List[CadConnectorInfoResponse])
def list_cad_connectors() -> List[CadConnectorInfoResponse]:
    connectors = sorted(cad_registry.list(), key=lambda info: info.id)
    return [
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
    ]


@cad_connectors_router.post(
    "/connectors/reload", response_model=CadConnectorReloadResponse
)
def reload_cad_connectors(
    req: CadConnectorReloadRequest,
    _: CurrentUser = Depends(require_admin_user),
) -> CadConnectorReloadResponse:
    settings = get_settings()
    config_path = req.config_path
    if config_path and not settings.CAD_CONNECTORS_ALLOW_PATH_OVERRIDE:
        raise HTTPException(
            status_code=403,
            detail="Path override disabled (set CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=true)",
        )
    if req.config is not None:
        result = reload_connectors(config_payload=req.config)
    else:
        result = reload_connectors(config_path=config_path)
    return CadConnectorReloadResponse(
        config_path=config_path or settings.CAD_CONNECTORS_CONFIG_PATH or None,
        custom_loaded=len(result.entries),
        errors=result.errors,
    )
