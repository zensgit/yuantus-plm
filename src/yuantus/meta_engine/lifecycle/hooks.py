"""
Lifecycle Hook System
支持before/after transition, on_enter/on_exit state
Phase 2.1
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.lifecycle.models import (
        LifecycleState,
        LifecycleTransition,
    )


class HookType(str, Enum):
    """Hook类型"""

    BEFORE_TRANSITION = "before_transition"
    AFTER_TRANSITION = "after_transition"
    ON_ENTER_STATE = "on_enter_state"
    ON_EXIT_STATE = "on_exit_state"
    ON_PROMOTE_FAIL = "on_promote_fail"


@dataclass
class HookContext:
    """Hook执行上下文"""

    item: "Item"
    user_id: int
    from_state: Optional["LifecycleState"]
    to_state: Optional["LifecycleState"]
    transition: Optional["LifecycleTransition"]
    extra_data: Dict[str, Any] = None

    # Hook可以设置这些来影响流程
    abort: bool = False
    abort_reason: str = ""
    modified_data: Dict[str, Any] = None


# Hook函数签名: (context: HookContext) -> None
HookFunction = Callable[[HookContext], None]


class LifecycleHookRegistry:
    """生命周期Hook注册表"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._hooks: Dict[str, List[tuple[int, HookFunction]]] = (
                {}
            )  # Store (priority, function)
        return cls._instance

    def register(
        self,
        item_type: str,
        hook_type: HookType,
        hook_fn: HookFunction,
        priority: int = 100,
    ) -> None:
        """
        注册Hook

        Args:
            item_type: ItemType名称，"*"表示全局
            hook_type: Hook类型
            hook_fn: Hook函数
            priority: 优先级，数字越小越先执行
        """
        key = f"{item_type}:{hook_type.value}"
        if key not in self._hooks:
            self._hooks[key] = []

        self._hooks[key].append((priority, hook_fn))
        self._hooks[key].sort(key=lambda x: x[0])  # Sort by priority

        logger.info(f"Registered hook: {key} with priority {priority}")

    def execute(
        self, item_type: str, hook_type: HookType, context: HookContext
    ) -> HookContext:
        """
        执行Hook链

        Returns:
            更新后的context，检查context.abort判断是否中止
        """
        # 先执行全局Hook
        global_key = f"*:{hook_type.value}"
        self._execute_hooks_for_key(global_key, context)

        if context.abort:
            return context

        # 再执行类型特定Hook
        type_key = f"{item_type}:{hook_type.value}"
        self._execute_hooks_for_key(type_key, context)

        return context

    def _execute_hooks_for_key(self, key: str, context: HookContext) -> None:
        """执行指定key的所有Hook"""
        hooks = self._hooks.get(key, [])

        for priority, hook_fn in hooks:
            try:
                hook_fn(context)
                if context.abort:
                    logger.warning(
                        f"Hook aborted: {hook_fn.__name__}, reason: {context.abort_reason}"
                    )
                    break
            except Exception as e:
                logger.error(f"Hook error: {hook_fn.__name__}, error: {e}")
                context.abort = True
                context.abort_reason = f"Hook error: {e}"
                break


# 全局注册表实例
hook_registry = LifecycleHookRegistry()


# 装饰器便捷注册
def lifecycle_hook(
    item_type: str = "*",
    hook_type: HookType = HookType.AFTER_TRANSITION,
    priority: int = 100,
):
    """
    Hook注册装饰器

    Usage:
        @lifecycle_hook("Document", HookType.AFTER_TRANSITION)
        def notify_on_release(context: HookContext):
            if context.to_state and context.to_state.name == "Released":
                # send_notification(context.item)
                pass
    """

    def decorator(fn: HookFunction):
        hook_registry.register(item_type, hook_type, fn, priority)
        return fn

    return decorator
