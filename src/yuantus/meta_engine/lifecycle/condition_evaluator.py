"""
Transition Condition Evaluator
支持JSON DSL定义的转换条件
Phase 2.2
"""

from typing import Any, Dict, Optional, Callable
from sqlalchemy.orm import Session
import logging

from yuantus.security.safe_evaluator import SafeExpressionEvaluator
from yuantus.meta_engine.models.item import Item  # For type hinting

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """
    转换条件求值器

    支持的条件格式:
    {
        "type": "and|or|not|field|expression|custom",
        "conditions": [...],  # for and/or
        "condition": {...},   # for not
        "field": "field_name",
        "operator": "eq|ne|gt|lt|gte|lte|in|contains|is_null",
        "value": any,
        "expression": "python_expression",  # for expression type
        "custom": "custom_check_name"  # for custom type
    }
    """

    def __init__(self, session: Session):
        self.session = session
        self.safe_evaluator = SafeExpressionEvaluator(
            allow_attributes=True
        )  # Allow attribute access for item properties
        self._custom_checks: Dict[str, Callable[[Item, int, Dict[str, Any]], bool]] = {}

    def register_custom_check(
        self, name: str, check_fn: Callable[[Item, int, Dict[str, Any]], bool]
    ) -> None:
        """注册自定义检查函数"""
        self._custom_checks[name] = check_fn

    def evaluate(
        self,
        condition: Dict[str, Any],
        item: Item,
        user_id: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        求值条件

        Args:
            condition: 条件定义
            item: 目标Item
            user_id: 操作用户
            context: 额外上下文

        Returns:
            条件是否满足
        """
        if not condition:
            return True

        cond_type = condition.get("type", "field")

        evaluators = {
            "and": self._eval_and,
            "or": self._eval_or,
            "not": self._eval_not,
            "field": self._eval_field,
            "expression": self._eval_expression,
            "custom": self._eval_custom,
        }

        evaluator_func = evaluators.get(cond_type)
        if not evaluator_func:
            logger.warning(f"Unknown condition type: {cond_type}")
            return True

        return evaluator_func(condition, item, user_id, context or {})

    def _eval_and(self, cond: Dict, item: Item, user_id: int, ctx: Dict) -> bool:
        """AND条件"""
        conditions = cond.get("conditions", [])
        return all(self.evaluate(c, item, user_id, ctx) for c in conditions)

    def _eval_or(self, cond: Dict, item: Item, user_id: int, ctx: Dict) -> bool:
        """OR条件"""
        conditions = cond.get("conditions", [])
        return any(self.evaluate(c, item, user_id, ctx) for c in conditions)

    def _eval_not(self, cond: Dict, item: Item, user_id: int, ctx: Dict) -> bool:
        """NOT条件"""
        inner = cond.get("condition", {})
        return not self.evaluate(inner, item, user_id, ctx)

    def _eval_field(self, cond: Dict, item: Item, user_id: int, ctx: Dict) -> bool:
        """字段条件"""
        field = cond.get("field")
        operator_str = cond.get("operator", "eq")
        expected_value = cond.get("value")

        # 获取字段值
        # item.to_dict() provides flattened access to properties
        item_data = item.to_dict()
        actual_value = self._get_field_value(item_data, field)  # Now get from dict

        # Compare
        operators = {
            "eq": lambda a, e: a == e,
            "ne": lambda a, e: a != e,
            "gt": lambda a, e: a > e,
            "lt": lambda a, e: a < e,
            "gte": lambda a, e: a >= e,
            "lte": lambda a, e: a <= e,
            "in": lambda a, e: a in e if isinstance(e, (list, tuple, set)) else False,
            "not in": lambda a, e: (
                a not in e if isinstance(e, (list, tuple, set)) else True
            ),
            "contains": lambda a, e: (
                e in a if isinstance(a, str) else False
            ),  # Check if string contains substring
            "is_null": lambda a, e: a is None if e else a is not None,
            "is_not_null": lambda a, e: a is not None if e else a is None,
        }

        op_func = operators.get(operator_str)
        if not op_func:
            logger.warning(f"Unknown operator: {operator_str}")
            return False  # Unknown operator should probably default to False

        try:
            return op_func(actual_value, expected_value)
        except Exception as e:
            logger.error(
                f"Field comparison error for field '{field}', operator '{operator_str}': {e}"
            )
            return False

    def _eval_expression(self, cond: Dict, item: Item, user_id: int, ctx: Dict) -> bool:
        """表达式条件"""
        expression = cond.get("expression", "True")

        # 构建求值环境
        env = {
            "item": item,
            "user_id": user_id,
            "properties": item.properties if item.properties else {},
            "state": item.state,  # Direct state access
            "current_state": item.current_state,  # Direct current_state FK access
            **ctx,
        }
        # Add item.to_dict() fields to context for easy access
        env.update(item.to_dict())

        try:
            return self.safe_evaluator.evaluate(expression, env)
        except Exception as e:
            logger.error(f"Expression evaluation failed: {e}")
            return False

    def _eval_custom(self, cond: Dict, item: Item, user_id: int, ctx: Dict) -> bool:
        """自定义检查"""
        check_name = cond.get("custom")
        check_fn = self._custom_checks.get(check_name)

        if not check_fn:
            logger.warning(f"Unknown custom check: {check_name}")
            return False  # Unknown custom check should default to False

        try:
            return check_fn(item, user_id, ctx)
        except Exception as e:
            logger.error(f"Custom check '{check_name}' failed: {e}")
            return False

    def _get_field_value(self, item_data: Dict[str, Any], field: str) -> Any:
        """获取字段值，支持点号路径"""
        parts = field.split(".")
        value = item_data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(
                value, part
            ):  # Allow attribute access for SQLAlchemy models within context
                value = getattr(value, part)
            else:
                return None  # Field not found at this level

        return value
