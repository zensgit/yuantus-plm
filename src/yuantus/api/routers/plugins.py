from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from yuantus.api.dependencies.auth import get_current_user
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.services.plugin_config_service import PluginConfigService

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
def list_plugins(request: Request) -> dict:
    manager = getattr(request.app.state, "plugin_manager", None)
    if not manager:
        return {"ok": True, "plugins": [], "stats": {"total": 0}}

    plugins = manager.list_plugins()
    return {
        "ok": True,
        "plugins": [p.to_dict() for p in plugins],
        "stats": manager.get_plugin_stats(),
    }


class PluginConfigPayload(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)
    merge: bool = Field(default=False)


@router.get("/{plugin_id}/config")
def get_plugin_config(
    plugin_id: str,
    request: Request,
    db=Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    manager = getattr(request.app.state, "plugin_manager", None)
    if not manager:
        raise HTTPException(status_code=404, detail="Plugin manager not initialized")
    plugin = manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    ctx = get_request_context()
    service = PluginConfigService(db)
    record = service.get_config(
        plugin_id=plugin_id, tenant_id=ctx.tenant_id, org_id=ctx.org_id
    )

    scope = (
        {"tenant_id": record.tenant_id, "org_id": record.org_id}
        if record
        else {"tenant_id": ctx.tenant_id, "org_id": ctx.org_id}
    )

    return {
        "ok": True,
        "plugin_id": plugin_id,
        "config": dict(record.config or {}) if record else {},
        "schema": plugin.metadata.config_schema or {},
        "capabilities": getattr(plugin.metadata, "capabilities", {}) or {},
        "created_at": record.created_at.isoformat() if record else None,
        "updated_at": record.updated_at.isoformat() if record else None,
        "scope": scope,
    }


@router.put("/{plugin_id}/config")
def update_plugin_config(
    plugin_id: str,
    payload: PluginConfigPayload,
    request: Request,
    db=Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    manager = getattr(request.app.state, "plugin_manager", None)
    if not manager:
        raise HTTPException(status_code=404, detail="Plugin manager not initialized")
    plugin = manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if not isinstance(payload.config, dict):
        raise HTTPException(status_code=400, detail="config must be an object")

    ctx = get_request_context()
    service = PluginConfigService(db)
    record = service.upsert_config(
        plugin_id=plugin_id,
        config=payload.config,
        tenant_id=ctx.tenant_id,
        org_id=ctx.org_id,
        user_id=getattr(current_user, "id", None),
        merge=payload.merge,
    )

    scope = {"tenant_id": record.tenant_id, "org_id": record.org_id}

    return {
        "ok": True,
        "plugin_id": plugin_id,
        "config": dict(record.config or {}),
        "schema": plugin.metadata.config_schema or {},
        "capabilities": getattr(plugin.metadata, "capabilities", {}) or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "scope": scope,
    }
