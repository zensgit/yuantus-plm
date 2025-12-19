from __future__ import annotations

from fastapi import APIRouter, Request

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

