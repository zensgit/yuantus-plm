"""
Lifecycle Manager - 插件生命周期管理
负责插件的激活、停用、回调执行等
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LifecycleManager:
    def activate_plugin(self, plugin) -> bool:
        try:
            return self._activate_plugin_instance(plugin)
        except Exception as exc:  # pragma: no cover
            logger.error(f"Plugin activation failed: {exc}")
            return False

    def deactivate_plugin(self, plugin) -> bool:
        try:
            return self._deactivate_plugin_instance(plugin)
        except Exception as exc:  # pragma: no cover
            logger.error(f"Plugin deactivation failed: {exc}")
            return False

    def _activate_plugin_instance(self, plugin) -> bool:
        plugin_instance = plugin.get_instance()

        if not plugin_instance:
            return self._activate_plugin_module(plugin)

        if hasattr(plugin_instance, "activate"):
            result = plugin_instance.activate()
            return result if isinstance(result, bool) else True

        if hasattr(plugin_instance, "start"):
            result = plugin_instance.start()
            return result if isinstance(result, bool) else True

        return True

    def _deactivate_plugin_instance(self, plugin) -> bool:
        plugin_instance = plugin.get_instance()

        if not plugin_instance:
            return self._deactivate_plugin_module(plugin)

        if hasattr(plugin_instance, "deactivate"):
            result = plugin_instance.deactivate()
            return result if isinstance(result, bool) else True

        if hasattr(plugin_instance, "stop"):
            result = plugin_instance.stop()
            return result if isinstance(result, bool) else True

        return True

    def _activate_plugin_module(self, plugin) -> bool:
        module = plugin.get_module()
        if not module:
            return False

        activate_functions = ["plugin_activate", "activate", "start", "main"]
        for func_name in activate_functions:
            if not hasattr(module, func_name):
                continue
            func = getattr(module, func_name)
            if not callable(func):
                continue
            try:
                result = func(plugin) if getattr(func, "__code__", None) and func.__code__.co_argcount > 0 else func()
                return result if isinstance(result, bool) else True
            except Exception as exc:
                logger.error(f"Module activation function {func_name} failed: {exc}")
                return False

        return True

    def _deactivate_plugin_module(self, plugin) -> bool:
        module = plugin.get_module()
        if not module:
            return True

        deactivate_functions = ["plugin_deactivate", "deactivate", "stop", "cleanup"]
        for func_name in deactivate_functions:
            if not hasattr(module, func_name):
                continue
            func = getattr(module, func_name)
            if not callable(func):
                continue
            try:
                result = func(plugin) if getattr(func, "__code__", None) and func.__code__.co_argcount > 0 else func()
                return result if isinstance(result, bool) else True
            except Exception as exc:
                logger.error(f"Module deactivation function {func_name} failed: {exc}")
                return False

        return True

