"""
Dependency Resolver - 插件依赖解析器
处理插件间的依赖关系和加载顺序
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """依赖类型"""

    REQUIRED = "required"  # 必需依赖
    OPTIONAL = "optional"  # 可选依赖
    CONFLICT = "conflict"  # 冲突依赖


@dataclass
class PluginDependency:
    """插件依赖"""

    plugin_id: str
    dependency_id: str
    dependency_type: DependencyType
    version_constraint: str = ""  # 版本约束，如 ">=1.0.0", "~1.2.0"
    reason: str = ""  # 依赖原因说明


class VersionComparator:
    """Simple semantic version comparator (MVP)."""

    def compare(self, v1: str, v2: str) -> int:
        def normalize(v: str) -> List[int]:
            parts: List[int] = []
            for token in (v or "").split("."):
                try:
                    parts.append(int(token))
                except ValueError:
                    parts.append(0)
            return parts

        a = normalize(v1)
        b = normalize(v2)
        n = max(len(a), len(b))
        a += [0] * (n - len(a))
        b += [0] * (n - len(b))
        if a < b:
            return -1
        if a > b:
            return 1
        return 0


class DependencyResolver:
    """依赖解析器"""

    def __init__(self) -> None:
        self._dependency_graph: Dict[str, List[PluginDependency]] = {}
        self._reverse_dependency_graph: Dict[str, List[str]] = {}
        self._version_comparator = VersionComparator()

    def add_plugin_dependencies(self, plugin) -> None:
        plugin_id = plugin.id
        metadata = plugin.metadata

        dependencies: List[PluginDependency] = []

        for dep_id in metadata.dependencies:
            dependencies.append(
                PluginDependency(
                    plugin_id=plugin_id,
                    dependency_id=dep_id,
                    dependency_type=DependencyType.REQUIRED,
                    reason="Required dependency",
                )
            )

        for dep_id in metadata.optional_dependencies:
            dependencies.append(
                PluginDependency(
                    plugin_id=plugin_id,
                    dependency_id=dep_id,
                    dependency_type=DependencyType.OPTIONAL,
                    reason="Optional dependency",
                )
            )

        for conflict_id in metadata.conflicts:
            dependencies.append(
                PluginDependency(
                    plugin_id=plugin_id,
                    dependency_id=conflict_id,
                    dependency_type=DependencyType.CONFLICT,
                    reason="Plugin conflict",
                )
            )

        self._dependency_graph[plugin_id] = dependencies

        for dep in dependencies:
            if dep.dependency_type == DependencyType.CONFLICT:
                continue
            self._reverse_dependency_graph.setdefault(dep.dependency_id, []).append(
                plugin_id
            )

    def resolve_dependencies(self, plugin) -> List[str]:
        plugin_id = plugin.id
        if plugin_id not in self._dependency_graph:
            self.add_plugin_dependencies(plugin)

        required_plugins = self._get_required_dependencies(plugin_id)
        load_order = self._topological_sort(required_plugins)
        if plugin_id in load_order:
            load_order.remove(plugin_id)
        return load_order

    def _get_required_dependencies(self, plugin_id: str) -> Set[str]:
        required: Set[str] = {plugin_id}
        stack = [plugin_id]

        while stack:
            pid = stack.pop()
            for dep in self._dependency_graph.get(pid, []):
                if dep.dependency_type != DependencyType.REQUIRED:
                    continue
                if dep.dependency_id in required:
                    continue
                required.add(dep.dependency_id)
                stack.append(dep.dependency_id)

        return required

    def _topological_sort(self, plugin_ids: Set[str]) -> List[str]:
        visited: Set[str] = set()
        temp: Set[str] = set()
        order: List[str] = []

        def visit(pid: str) -> None:
            if pid in visited:
                return
            if pid in temp:
                raise ValueError(f"Circular dependency detected at {pid}")
            temp.add(pid)
            for dep in self._dependency_graph.get(pid, []):
                if dep.dependency_type != DependencyType.REQUIRED:
                    continue
                if dep.dependency_id in plugin_ids:
                    visit(dep.dependency_id)
            temp.remove(pid)
            visited.add(pid)
            order.append(pid)

        for pid in sorted(plugin_ids):
            visit(pid)

        return order

