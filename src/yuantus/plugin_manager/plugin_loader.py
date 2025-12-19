"""
Plugin Loader - 插件加载器
负责插件的动态加载和卸载
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class PluginLoadResult:
    """插件加载结果"""

    success: bool
    plugin_id: str
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class PluginLoader:
    """插件加载器"""

    def __init__(self) -> None:
        self._loaded_modules: Dict[str, Any] = {}
        self._plugin_classes: Dict[str, Type] = {}
        self._module_paths: Dict[str, Path] = {}

    def load_plugin(self, plugin) -> PluginLoadResult:
        plugin_id = plugin.id
        plugin_path = plugin.plugin_path
        entry_point = plugin.metadata.entry_point

        result = PluginLoadResult(success=False, plugin_id=plugin_id)
        try:
            module_path = plugin_path / entry_point
            if not module_path.exists():
                result.error_message = f"Entry point not found: {module_path}"
                return result

            if module_path.is_file() and module_path.suffix != ".py":
                result.error_message = f"Entry point must be a Python file: {module_path}"
                return result

            if module_path.is_dir() and not (module_path / "__init__.py").exists():
                result.error_message = (
                    f"Package entry point missing __init__.py: {module_path}"
                )
                return result

            module = self._import_module(plugin_id, module_path)
            if not module:
                result.error_message = f"Failed to import module: {module_path}"
                return result

            self._loaded_modules[plugin_id] = module
            self._module_paths[plugin_id] = module_path
            plugin.set_module(module)

            plugin_class = self._find_plugin_class(module, plugin)
            if plugin_class:
                instantiated = False
                try:
                    plugin_instance = plugin_class(plugin)
                    instantiated = True
                except TypeError:
                    try:
                        plugin_instance = plugin_class()
                        instantiated = True
                    except Exception:
                        instantiated = False
                except Exception:
                    result.warnings.append(
                        f"Plugin class ctor raised, trying fallbacks: {traceback.format_exc()}"
                    )

                if not instantiated and hasattr(module, "plugin_instance"):
                    try:
                        plugin_instance = getattr(module, "plugin_instance")
                        instantiated = True
                    except Exception:
                        instantiated = False

                if instantiated:
                    plugin.set_instance(plugin_instance)
                    self._plugin_classes[plugin_id] = plugin_class
                else:
                    result.warnings.append(
                        "No instantiable plugin class; proceeding without instance"
                    )
            else:
                result.warnings.append("No plugin class found, using module as plugin")

            if hasattr(module, "plugin_init"):
                try:
                    module.plugin_init(plugin)
                except Exception as exc:
                    result.warnings.append(f"Plugin initialization warning: {exc}")

            result.success = True
            return result
        except Exception as exc:
            result.error_message = str(exc)
            result.warnings.append(traceback.format_exc())
            return result

    def unload_plugin(self, plugin) -> bool:
        plugin_id = plugin.id
        try:
            module = self._loaded_modules.get(plugin_id)
            if not module:
                return True

            if hasattr(module, "plugin_unload"):
                try:
                    module.plugin_unload(plugin)
                except Exception as exc:
                    logger.warning(f"plugin_unload warning for {plugin_id}: {exc}")

            self._cleanup_module_references(plugin_id)

            self._loaded_modules.pop(plugin_id, None)
            self._plugin_classes.pop(plugin_id, None)
            self._module_paths.pop(plugin_id, None)
            return True
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to unload plugin {plugin_id}: {exc}")
            return False

    def reload_plugin(self, plugin) -> PluginLoadResult:
        plugin_id = plugin.id
        if not self.unload_plugin(plugin):
            return PluginLoadResult(
                success=False,
                plugin_id=plugin_id,
                error_message="Failed to unload plugin for reload",
            )

        if plugin_id in self._loaded_modules:
            module = self._loaded_modules[plugin_id]
            try:
                importlib.reload(module)
            except Exception:
                pass

        return self.load_plugin(plugin)

    def _import_module(self, plugin_id: str, module_path: Path):
        try:
            module_name = f"yuantus_plugin_{plugin_id.replace('-', '_')}"
            if module_path.is_file():
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if not spec or not spec.loader:
                    return None
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            else:
                spec = importlib.util.spec_from_file_location(
                    module_name, module_path / "__init__.py"
                )
                if not spec or not spec.loader:
                    return None
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            return module
        except Exception as exc:
            logger.error(f"Failed to import module {module_path}: {exc}")
            logger.debug(f"Import traceback: {traceback.format_exc()}")
            return None

    def _find_plugin_class(self, module, plugin):
        plugin_id = plugin.id
        candidates: List[tuple[type, int]] = []

        for name in dir(module):
            obj = getattr(module, name)
            if not isinstance(obj, type):
                continue
            if obj.__module__ != module.__name__:
                continue

            if name == "Plugin":
                candidates.append((obj, 100))
                continue
            if self._is_plugin_class(obj):
                candidates.append((obj, 90))
                continue
            if name.endswith("Plugin"):
                candidates.append((obj, 80))
                continue

            normalized_id = plugin_id.replace("-", "_").replace(" ", "_")
            if name.lower() == normalized_id.lower():
                candidates.append((obj, 70))
                continue
            if normalized_id.lower() in name.lower():
                candidates.append((obj, 60))
                continue

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _is_plugin_class(self, cls) -> bool:
        plugin_methods = ["activate", "deactivate", "get_info", "configure"]
        plugin_attributes = ["name", "version", "description"]

        method_score = sum(1 for method in plugin_methods if hasattr(cls, method))
        attr_score = sum(1 for attr in plugin_attributes if hasattr(cls, attr))

        return method_score >= 2 or (method_score >= 1 and attr_score >= 1)

    def _cleanup_module_references(self, plugin_id: str) -> None:
        module_name = f"yuantus_plugin_{plugin_id.replace('-', '_')}"
        modules_to_remove = [name for name in sys.modules if name.startswith(module_name)]
        for name in modules_to_remove:
            sys.modules.pop(name, None)

