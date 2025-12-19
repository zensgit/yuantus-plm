from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

from fastapi import APIRouter, FastAPI

from yuantus.config import get_settings
from yuantus.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


def _parse_csv(value: str) -> list[str]:
    return [p.strip() for p in (value or "").split(",") if p.strip()]


def _iter_routers(obj) -> Iterable[APIRouter]:
    if obj is None:
        return []

    if isinstance(obj, APIRouter):
        return [obj]

    if hasattr(obj, "get_routers") and callable(getattr(obj, "get_routers")):
        try:
            routers = obj.get_routers()
            if isinstance(routers, APIRouter):
                return [routers]
            if isinstance(routers, list):
                return [r for r in routers if isinstance(r, APIRouter)]
        except Exception:
            return []

    if hasattr(obj, "routers"):
        routers = getattr(obj, "routers")
        if isinstance(routers, APIRouter):
            return [routers]
        if isinstance(routers, list):
            return [r for r in routers if isinstance(r, APIRouter)]

    if hasattr(obj, "router") and isinstance(getattr(obj, "router"), APIRouter):
        return [getattr(obj, "router")]

    return []


def load_plugins(app: FastAPI) -> Optional[PluginManager]:
    """
    Discover/load/activate plugins and mount plugin routers (if provided).

    Router mount rule:
    - Plugin provides APIRouter with its own prefix (e.g. `/plugins/demo`)
    - Yuantus mounts it under `/api/v1`
    """
    settings = get_settings()
    plugin_dirs = [Path(p) for p in _parse_csv(getattr(settings, "PLUGIN_DIRS", ""))]
    plugin_dirs = [p for p in plugin_dirs if str(p)]
    if not plugin_dirs:
        return None

    manager = PluginManager(plugin_dirs)
    manager.discover_plugins()

    # Attach for observability (API can expose it)
    app.state.plugin_manager = manager

    enabled = set(_parse_csv(getattr(settings, "PLUGINS_ENABLED", "")))
    autoload = bool(getattr(settings, "PLUGINS_AUTOLOAD", False))

    if not autoload:
        return manager

    for plugin in manager.list_plugins():
        if enabled and plugin.id not in enabled:
            continue
        if not manager.load_plugin(plugin.id):
            logger.warning(f"Plugin load failed: {plugin.id}")
            continue
        if not manager.activate_plugin(plugin.id):
            logger.warning(f"Plugin activate failed: {plugin.id}")
            continue

        module = plugin.get_module()
        instance = plugin.get_instance()
        for router in list(_iter_routers(instance)) + list(_iter_routers(module)):
            app.include_router(router, prefix="/api/v1")

    return manager

