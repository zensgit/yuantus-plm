from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from yuantus.config import get_settings
from yuantus.plugin_manager.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _iter_register_targets(plugin) -> Iterable[object]:
    instance = plugin.get_instance()
    module = plugin.get_module()
    if instance is not None:
        yield instance
    if module is not None:
        yield module


def register_plugin_job_handlers(worker) -> int:
    settings = get_settings()
    plugin_dirs = [Path(p) for p in _parse_csv(getattr(settings, "PLUGIN_DIRS", ""))]
    plugin_dirs = [p for p in plugin_dirs if str(p)]
    if not plugin_dirs:
        return 0

    manager = PluginManager(plugin_dirs)
    manager.discover_plugins()

    enabled = set(_parse_csv(getattr(settings, "PLUGINS_ENABLED", "")))
    autoload = bool(getattr(settings, "PLUGINS_AUTOLOAD", False))
    registered = 0

    for plugin in manager.list_plugins():
        if enabled and plugin.id not in enabled:
            continue
        if not manager.load_plugin(plugin.id):
            logger.warning("Plugin load failed for job handlers: %s", plugin.id)
            continue
        if autoload and not manager.activate_plugin(plugin.id):
            logger.warning("Plugin activation failed for job handlers: %s", plugin.id)

        for target in _iter_register_targets(plugin):
            register = getattr(target, "register_job_handlers", None)
            if not callable(register):
                continue
            try:
                register(worker)
                registered += 1
            except Exception as exc:
                logger.warning(
                    "Plugin job handler registration failed (%s): %s",
                    plugin.id,
                    exc,
                )

    return registered

