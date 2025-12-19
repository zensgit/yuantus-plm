"""
IR Rule Compatibility Adapter
Parses Odoo-style domain filters and checks permissions.
ADR-002: Retrofit legacy rules.
"""

import ast
from typing import List, Tuple, Any, Dict
from sqlalchemy.sql.expression import and_, or_
from sqlalchemy.orm.query import Query
from sqlalchemy import inspection


class IRRuleAdapter:
    """
    Adapts Odoo 'ir.rule' domains to SQLAlchemy filters.
    Example domain: [('state', '=', 'draft'), ('user_id', '=', user.id)]
    """

    def __init__(self, user_context: Dict[str, Any]):
        """
        Args:
            user_context: Dict containing 'user' object (with id, company_id) similar to Odoo env.
        """
        self.user = user_context.get("user")
        self.user_id = self.user.id if self.user else None

    def eval_domain(self, domain_str: str) -> List[Tuple]:
        """
        Safely evaluates string representation of list validation domain.
        Replaces 'user.id' etc with actual values.
        """
        # 1. Parse string literal to list
        # CAUTION: 'eval' is dangerous. In production, use a safe parser or restrictive environment.
        # Here we do string substitution for known variables then literal_eval

        ctx_str = domain_str.replace("user.id", str(self.user_id))
        ctx_str = ctx_str.replace("True", "True").replace(
            "False", "False"
        )  # Odoo allow boolean constants

        try:
            raw_domain = ast.literal_eval(ctx_str)
        except Exception as e:
            # Fallback for complex expressions not supported in this simple adapter
            # e.g. [('company_id', 'in', [1,2,3])]
            print(f"Failed to parse domain: {e}")
            return []

        return raw_domain

    def apply_domain(self, query: Query, model_class, domain: List[Tuple]) -> Query:
        """
        Applies the Odoo-style domain to a SQLAlchemy query.

        Supported operators: =, !=, >, <, >=, <=, in, not in, ilike
        """

        # Odoo domains are implicitly AND, but support ['|', A, B] for OR logic (Polish notation).
        # Implementing full Polish notation parser is complex.
        # Focusing on simple [A, B, C] -> A AND B AND C
        # We'll just process linear lists as AND for MVP.
        # If we encounter '|', we need a stack.

        def process_leaf(leaf):
            if isinstance(leaf, str) and leaf in ["|", "&", "!"]:
                return leaf

            field_name, operator, value = leaf

            # Map field name to model column
            # Special case: properties (JSONB)
            # If field not in columns, assume properties

            mapper = inspection.inspect(model_class)
            column = None
            if field_name in mapper.columns:
                column = getattr(model_class, field_name)
            else:
                # Assume property in JSONB 'properties'
                # cast to text for string comparison
                json_expr = model_class.properties[field_name]
                if hasattr(json_expr, "as_string"):
                    column = json_expr.as_string()
                elif hasattr(json_expr, "astext"):
                    column = json_expr.astext
                else:
                    column = json_expr

            if column is None:
                return None

            if operator == "=":
                return column == value
            elif operator == "!=":
                return column != value
            elif operator == ">":
                return column > value
            elif operator == "<":
                return column < value
            elif operator == ">=":
                return column >= value
            elif operator == "<=":
                return column <= value
            elif operator == "in":
                return column.in_(value)
            elif operator == "not in":
                return ~column.in_(value)
            elif operator == "ilike":
                return column.ilike(value)

            return None

        # Basic Recursive Parser for Polish Notation (Prefix)
        # Domain: ['|', ('a','=',1), ('b','=',2)] -> OR(a=1, b=2)
        # Domain: [('a','=',1), ('b','=',2)] -> AND(a=1, b=2) (implicit AND)

        def build_expression(items):
            if not items:
                return None

            token = items[0]
            if token == "&":
                items.pop(0)
                left = build_expression(items)
                right = build_expression(items)
                return and_(left, right)
            elif token == "|":
                items.pop(0)
                left = build_expression(items)
                right = build_expression(items)
                return or_(left, right)
            elif token == "!":
                items.pop(0)
                expr = build_expression(items)
                return ~expr
            else:
                # Leaf tuple
                items.pop(0)
                return process_leaf(token)

        # Pre-process: if implicit AND (no leading operator), assume &...&
        # But wait, Odoo list [A, B, C] is AND(AND(A, B), C).
        # We need to insert '&' if missing.
        # Or easier: just use filter(and_(*expressions)) if no polish notation.

        # Check for operators
        has_logic_ops = any(isinstance(x, str) for x in domain)

        if has_logic_ops:
            # Full parser needed (Deep copy to consume)
            expr = build_expression(list(domain))
            if expr is not None:
                query = query.filter(expr)
        else:
            # Simple AND list
            for leaf in domain:
                expr = process_leaf(leaf)
                if expr is not None:
                    query = query.filter(expr)

        return query
