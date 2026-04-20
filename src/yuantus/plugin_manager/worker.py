from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from yuantus.config import get_settings
from yuantus.plugin_manager.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _should_bootstrap_plugins(*, autoload: bool, enabled: set[str]) -> bool:
    return autoload or bool(enabled)


def _should_load_plugin(plugin_id: str, *, autoload: bool, enabled: set[str]) -> bool:
    return plugin_id in enabled if enabled else autoload


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

    enabled = set(_parse_csv(getattr(settings, "PLUGINS_ENABLED", "")))
    autoload = bool(getattr(settings, "PLUGINS_AUTOLOAD", False))
    registered = 0

    if not _should_bootstrap_plugins(autoload=autoload, enabled=enabled):
        logger.info(
            "Plugin job handler registration skipped: autoload disabled and no plugins explicitly enabled"
        )
        return 0

    manager = PluginManager(plugin_dirs)
    manager.discover_plugins()

    for plugin in manager.list_plugins():
        if not _should_load_plugin(plugin.id, autoload=autoload, enabled=enabled):
            continue
        if not manager.load_plugin(plugin.id):
            logger.warning("Plugin load failed for job handlers: %s", plugin.id)
            continue
        if not manager.activate_plugin(plugin.id):
            logger.warning("Plugin activation failed for job handlers: %s", plugin.id)
            continue

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
