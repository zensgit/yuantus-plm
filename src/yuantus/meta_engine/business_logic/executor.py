import importlib
from typing import Optional
from sqlalchemy.orm import Session
from .models import Method, MethodType
from ..models.item import Item
from ..schemas.aml import GenericItem


class MethodExecutor:
    def __init__(self, session: Session):
        self.session = session

    def execute_method(
        self, method_id: str, context_item: Item, payload: Optional[GenericItem] = None
    ) -> Item:
        """
        执行方法
        Args:
            method_id: 方法ID
            context_item: 当前操作的 Item 对象 (会被修改)
            payload: 原始 AML 请求
        Returns:
            修改后的 Item
        """
        method_def = self.session.get(Method, method_id)
        if not method_def:
            # 容错：如果找不到方法，忽略而不阻断
            return context_item

        if (
            method_def.type == MethodType.PYTHON_MODULE
            or method_def.type == "python_module"
        ):
            return self._run_module(method_def.content, context_item, payload)

        if (
            method_def.type == MethodType.PYTHON_SCRIPT
            or method_def.type == "python_script"
        ):
            return self._run_script(method_def, context_item, payload)

        return context_item

    def _run_script(
        self, method: Method, item: Item, payload: Optional[GenericItem]
    ) -> Item:
        """
        Execute raw Python code stored in DB.
        Vars in scope: 'session', 'item', 'payload'
        """
        code = method.content
        if not code:
            return item

        local_scope = {
            "session": self.session,
            "item": item,
            "payload": payload,
            # Add other utils if needed
        }

        try:
            exec(code, {}, local_scope)
            # We assume script modifies 'item' in place.
            # Optional: Allow script to set 'result' variable if it wants to return a NEW item instance?
            # For now, in-place modification is sufficient for hooks.
            return item
        except Exception as e:
            # Re-raise to block transaction
            raise ValueError(f"Error executing Method '{method.name}': {str(e)}") from e

    def _run_module(self, module_path: str, item: Item, payload: GenericItem) -> Item:
        """
        动态导入 Python 模块并执行其 entry point
        约定入口函数签名为: def run(session, item, payload) -> Item
        """
        try:
            # e.g. "plm_extensions.part_hooks"
            module = importlib.import_module(module_path)
            if hasattr(module, "run"):
                # Pass session to allow DB queries inside hook (e.g. check duplicate)
                result = module.run(self.session, item, payload)
                return result or item
        except ImportError as e:
            print(f"Failed to import hook {module_path}: {e}")
            # log warning
        except Exception as e:
            # 业务逻辑报错应该阻断事务吗？Aras 默认是 yes。
            raise e

        return item
