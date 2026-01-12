"""
Plugin Manager - 插件管理器核心
管理插件的加载、卸载和生命周期
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """插件状态"""

    UNKNOWN = "unknown"
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    INACTIVE = "inactive"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """插件元数据"""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = ""

    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)

    python_version: str = ""
    plm_version: str = ""
    platforms: List[str] = field(default_factory=list)

    plugin_type: str = "extension"
    category: str = "general"
    tags: List[str] = field(default_factory=list)

    config_schema: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    api_version: str = "1.0"

    hooks: Dict[str, str] = field(default_factory=dict)

    entry_point: str = ""
    assets: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Plugin:
    """插件对象"""

    def __init__(self, metadata: PluginMetadata, plugin_path: Path):
        self.metadata = metadata
        self.plugin_path = plugin_path
        self.status = PluginStatus.DISCOVERED

        self._module = None
        self._instance = None
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()

        self._lifecycle_callbacks: Dict[str, List[Callable]] = {
            "on_load": [],
            "on_activate": [],
            "on_deactivate": [],
            "on_unload": [],
            "on_error": [],
        }

        self.loaded_at: Optional[datetime] = None
        self.activated_at: Optional[datetime] = None
        self.error_count = 0
        self.last_error: Optional[str] = None

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def is_loaded(self) -> bool:
        return self.status in [PluginStatus.LOADED, PluginStatus.ACTIVE]

    @property
    def is_active(self) -> bool:
        return self.status == PluginStatus.ACTIVE

    @property
    def has_errors(self) -> bool:
        return self.status == PluginStatus.ERROR or self.error_count > 0

    def set_module(self, module) -> None:
        with self._lock:
            self._module = module

    def get_module(self):
        with self._lock:
            return self._module

    def set_instance(self, instance) -> None:
        with self._lock:
            self._instance = instance

    def get_instance(self):
        with self._lock:
            return self._instance

    def record_error(self, error: str) -> None:
        with self._lock:
            self.error_count += 1
            self.last_error = error
            if self.status != PluginStatus.ERROR:
                self.status = PluginStatus.ERROR

        self._trigger_callbacks("on_error", error)

    def _trigger_callbacks(self, event: str, *args, **kwargs) -> None:
        callbacks = self._lifecycle_callbacks.get(event, [])
        for callback in callbacks:
            try:
                callback(self, *args, **kwargs)
            except Exception as exc:
                logger.error(f"Plugin callback failed: {exc}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "status": self.status.value,
            "is_active": self.is_active,
            "plugin_type": self.metadata.plugin_type,
            "category": self.metadata.category,
            "tags": self.metadata.tags,
            "dependencies": self.metadata.dependencies,
            "config_schema": self.metadata.config_schema,
            "capabilities": self.metadata.capabilities,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "plugin_path": str(self.plugin_path),
        }


class PluginManager:
    """插件管理器"""

    def __init__(self, plugin_directories: Optional[List[Path]] = None):
        if plugin_directories is None:
            self.plugin_directories: List[Path] = []
        else:
            self.plugin_directories = [Path(p) for p in plugin_directories]

        self._plugins: Dict[str, Plugin] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._shutdown = False

        from .dependency_resolver import DependencyResolver
        from .lifecycle_manager import LifecycleManager
        from .plugin_loader import PluginLoader

        self.loader = PluginLoader()
        self.dependency_resolver = DependencyResolver()
        self.lifecycle_manager = LifecycleManager()

    def add_plugin_directory(self, directory: Path) -> None:
        if directory not in self.plugin_directories:
            self.plugin_directories.append(directory)

    def discover_plugins(self) -> List[Plugin]:
        discovered_plugins: List[Plugin] = []
        for directory in self.plugin_directories:
            if not directory.exists():
                continue
            for item in directory.iterdir():
                if not item.is_dir():
                    continue
                plugin = self._discover_plugin(item)
                if plugin:
                    discovered_plugins.append(plugin)
        return discovered_plugins

    def _discover_plugin(self, plugin_path: Path) -> Optional[Plugin]:
        try:
            manifest_files = ["plugin.json", "manifest.json", "plugin.yaml", "plugin.yml"]
            manifest_path: Optional[Path] = None
            for manifest_file in manifest_files:
                candidate = plugin_path / manifest_file
                if candidate.exists():
                    manifest_path = candidate
                    break

            if not manifest_path:
                return None

            metadata = self._parse_plugin_metadata(manifest_path)
            if not metadata:
                return None

            with self._lock:
                if metadata.id in self._plugins:
                    return None
                plugin = Plugin(metadata, plugin_path)
                self._plugins[metadata.id] = plugin

            return plugin
        except Exception as exc:
            logger.error(f"Failed to discover plugin in {plugin_path}: {exc}")
            return None

    def _parse_plugin_metadata(self, manifest_path: Path) -> Optional[PluginMetadata]:
        try:
            if manifest_path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml  # type: ignore
                except Exception:
                    raise RuntimeError("PyYAML is required to load YAML manifests")
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            else:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            if not isinstance(data, dict):
                return None

            for field_name in ["id", "name", "version"]:
                if field_name not in data:
                    return None

            return PluginMetadata(
                id=data["id"],
                name=data["name"],
                version=data["version"],
                description=data.get("description", ""),
                author=data.get("author", ""),
                homepage=data.get("homepage", ""),
                license=data.get("license", ""),
                dependencies=data.get("dependencies", []),
                optional_dependencies=data.get("optional_dependencies", []),
                conflicts=data.get("conflicts", []),
                python_version=data.get("python_version", ""),
                plm_version=data.get("plm_version", ""),
                platforms=data.get("platforms", []),
                plugin_type=data.get("plugin_type", "extension"),
                category=data.get("category", "general"),
                tags=data.get("tags", []),
                config_schema=data.get("config_schema", {}),
                capabilities=data.get("capabilities", {}),
                permissions=data.get("permissions", []),
                api_version=data.get("api_version", "1.0"),
                hooks=data.get("hooks", {}),
                entry_point=data.get("entry_point", "main.py"),
                assets=data.get("assets", []),
                templates=data.get("templates", []),
            )
        except Exception as exc:
            logger.error(f"Failed to parse plugin metadata from {manifest_path}: {exc}")
            return None

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        with self._lock:
            return self._plugins.get(plugin_id)

    def list_plugins(
        self,
        *,
        status: Optional[PluginStatus] = None,
        plugin_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Plugin]:
        with self._lock:
            plugins = list(self._plugins.values())

        if status is not None:
            plugins = [p for p in plugins if p.status == status]
        if plugin_type is not None:
            plugins = [p for p in plugins if p.metadata.plugin_type == plugin_type]
        if category is not None:
            plugins = [p for p in plugins if p.metadata.category == category]
        return plugins

    def load_plugin(self, plugin_id: str) -> bool:
        with self._lock:
            plugin = self._plugins.get(plugin_id)
            if not plugin:
                return False
            if plugin.is_loaded:
                return True
            plugin.status = PluginStatus.LOADING

        try:
            dependencies = self.dependency_resolver.resolve_dependencies(plugin)
            for dep_id in dependencies:
                if dep_id not in self._plugins:
                    plugin.record_error(f"Missing dependency: {dep_id}")
                    return False
                if not self.load_plugin(dep_id):
                    plugin.record_error(f"Failed to load dependency: {dep_id}")
                    return False

            load_result = self.loader.load_plugin(plugin)
            if not load_result.success:
                plugin.record_error(load_result.error_message or "Unknown load error")
                return False

            plugin.status = PluginStatus.LOADED
            plugin.loaded_at = datetime.now(timezone.utc)
            plugin._trigger_callbacks("on_load")
            return True
        except Exception as exc:
            plugin.record_error(str(exc))
            return False

    def activate_plugin(self, plugin_id: str) -> bool:
        with self._lock:
            plugin = self._plugins.get(plugin_id)
            if not plugin:
                return False
            if plugin.is_active:
                return True
            if not plugin.is_loaded and not self.load_plugin(plugin_id):
                return False
            plugin.status = PluginStatus.ACTIVATING

        try:
            success = self.lifecycle_manager.activate_plugin(plugin)
            if not success:
                plugin.status = PluginStatus.LOADED
                plugin.record_error("Plugin activation failed")
                return False

            plugin.status = PluginStatus.ACTIVE
            plugin.activated_at = datetime.now(timezone.utc)
            plugin._trigger_callbacks("on_activate")
            return True
        except Exception as exc:
            plugin.status = PluginStatus.LOADED
            plugin.record_error(str(exc))
            return False

    def deactivate_plugin(self, plugin_id: str) -> bool:
        with self._lock:
            plugin = self._plugins.get(plugin_id)
            if not plugin:
                return False
            if not plugin.is_active:
                return True
            plugin.status = PluginStatus.DEACTIVATING

        try:
            success = self.lifecycle_manager.deactivate_plugin(plugin)
            if not success:
                plugin.status = PluginStatus.ACTIVE
                plugin.record_error("Plugin deactivation failed")
                return False
            plugin.status = PluginStatus.LOADED
            plugin._trigger_callbacks("on_deactivate")
            return True
        except Exception as exc:
            plugin.status = PluginStatus.ACTIVE
            plugin.record_error(str(exc))
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        with self._lock:
            plugin = self._plugins.get(plugin_id)
            if not plugin:
                return False
            if not plugin.is_loaded:
                return True
            if plugin.is_active and not self.deactivate_plugin(plugin_id):
                return False
            plugin.status = PluginStatus.UNLOADING

        try:
            success = self.loader.unload_plugin(plugin)
            if not success:
                plugin.status = PluginStatus.LOADED
                plugin.record_error("Plugin unload failed")
                return False

            plugin.status = PluginStatus.UNLOADED
            plugin.set_module(None)
            plugin.set_instance(None)
            plugin.loaded_at = None
            plugin.activated_at = None
            plugin._trigger_callbacks("on_unload")
            return True
        except Exception as exc:
            plugin.status = PluginStatus.LOADED
            plugin.record_error(str(exc))
            return False

    def get_plugin_stats(self) -> Dict[str, Any]:
        with self._lock:
            by_status: Dict[str, int] = {}
            by_type: Dict[str, int] = {}
            by_category: Dict[str, int] = {}
            stats: Dict[str, Any] = {
                "total": len(self._plugins),
                "by_status": by_status,
                "by_type": by_type,
                "by_category": by_category,
                "errors": 0,
            }

            for plugin in self._plugins.values():
                by_status[plugin.status.value] = by_status.get(plugin.status.value, 0) + 1
                by_type[plugin.metadata.plugin_type] = by_type.get(plugin.metadata.plugin_type, 0) + 1
                by_category[plugin.metadata.category] = by_category.get(plugin.metadata.category, 0) + 1
                if plugin.has_errors:
                    stats["errors"] += 1

            return stats

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        try:
            for plugin in self.list_plugins(status=PluginStatus.ACTIVE):
                try:
                    self.deactivate_plugin(plugin.id)
                except Exception:
                    pass
            for plugin in self.list_plugins():
                if plugin.is_loaded:
                    try:
                        self.unload_plugin(plugin.id)
                    except Exception:
                        pass
            self._executor.shutdown(wait=True)
        except Exception:
            pass
