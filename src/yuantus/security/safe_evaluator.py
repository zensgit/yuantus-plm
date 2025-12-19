"""
Safe Expression Evaluator for YuantusPLM.

Copied from the existing PLM baseline to avoid unsafe eval().
"""

from __future__ import annotations

import ast
import json
import logging
import operator
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class SafeExpressionEvaluator:
    OPERATORS: Dict[type, Callable[..., Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.And: lambda *args: all(args),
        ast.Or: lambda *args: any(args),
        ast.Not: operator.not_,
    }

    SAFE_FUNCTIONS: Dict[str, Callable[..., Any]] = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        "sorted": sorted,
        "any": any,
        "all": all,
        "json": json.loads,
    }

    SAFE_CONSTANTS: Dict[str, Any] = {
        "True": True,
        "False": False,
        "None": None,
    }

    def __init__(self, context: Optional[Dict[str, Any]] = None, *, allow_attributes: bool = False):
        self.context = context or {}
        self.allow_attributes = allow_attributes
        self._max_string_length = 10_000
        self._max_list_length = 1_000

    def evaluate(self, expression: str) -> Any:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            stmt_tree = ast.parse(expression, mode="exec")
            self._validate_ast(stmt_tree)
            raise ValueError("Only pure expressions are allowed")

        self._validate_ast(tree)
        return self._eval_node(tree.body)

    def _validate_ast(self, node: ast.AST) -> None:
        for child in ast.walk(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                raise ValueError("Import statements are not allowed")
            if isinstance(child, (ast.FunctionDef, ast.ClassDef)):
                raise ValueError("Function/class definitions are not allowed")
            if type(child).__name__ == "Exec":
                raise ValueError("Exec statements are not allowed")
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id not in self.SAFE_FUNCTIONS:
                    raise ValueError(f"Function '{child.func.id}' is not allowed")
            if isinstance(child, ast.Attribute) and not self.allow_attributes:
                raise ValueError("Attribute access is not allowed")

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            name = node.id
            if name in self.SAFE_CONSTANTS:
                return self.SAFE_CONSTANTS[name]
            if name in self.context:
                return self.context[name]
            raise ValueError(f"Undefined variable: {name}")
        if isinstance(node, ast.List):
            items = [self._eval_node(item) for item in node.elts]
            if len(items) > self._max_list_length:
                raise ValueError(f"List too long (max {self._max_list_length} items)")
            return items
        if isinstance(node, ast.Dict):
            result: Dict[Any, Any] = {}
            for k_node, v_node in zip(node.keys, node.values):
                if k_node is None:
                    raise ValueError("Dict unpacking is not allowed")
                result[self._eval_node(k_node)] = self._eval_node(v_node)
            return result
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item) for item in node.elts)
        if isinstance(node, ast.Set):
            return set(self._eval_node(item) for item in node.elts)
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_func(left, right)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_func(operand)
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_func = self.OPERATORS.get(type(op_node))
                if op_func is None:
                    raise ValueError(f"Unsupported comparison: {type(op_node).__name__}")
                if not op_func(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            values = [self._eval_node(v) for v in node.values]
            bool_op_func = self.OPERATORS.get(type(node.op))
            if bool_op_func is None:
                raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")
            return bool_op_func(*values)
        if isinstance(node, ast.IfExp):
            return self._eval_node(node.body) if self._eval_node(node.test) else self._eval_node(node.orelse)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are allowed")
            func = self.SAFE_FUNCTIONS.get(node.func.id)
            if not func:
                raise ValueError(f"Function '{node.func.id}' is not allowed")
            args = [self._eval_node(a) for a in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value) for kw in node.keywords if kw.arg}
            return func(*args, **kwargs)

        raise ValueError(f"Unsupported expression: {type(node).__name__}")

