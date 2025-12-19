from unittest.mock import MagicMock
from yuantus.meta_engine.parsers.ir_rule_adapter import IRRuleAdapter
from yuantus.meta_engine.parsers.odoo_mocks import MagicUser
from yuantus.meta_engine.models.item import Item


class TestIRRuleAdapter:
    def test_eval_domain_simple(self):
        user = MagicUser(99)
        adapter = IRRuleAdapter({"user": user})

        domain_str = "[('state', '=', 'draft'), ('created_by_id', '=', user.id)]"
        res = adapter.eval_domain(domain_str)

        assert len(res) == 2
        assert res[0] == ("state", "=", "draft")
        assert res[1] == ("created_by_id", "=", 99)

    def test_apply_domain_simple_and(self):
        user = MagicUser(99)
        adapter = IRRuleAdapter({"user": user})
        domain = [("state", "=", "draft"), ("current_version_id", "!=", None)]

        query = MagicMock()
        query.filter.return_value = query  # Chainable

        adapter.apply_domain(query, Item, domain)

        assert query.filter.call_count == 2

    def test_apply_domain_polish_or(self):
        adapter = IRRuleAdapter({})
        domain = ["|", ("state", "=", "draft"), ("state", "=", "reviewed")]

        query = MagicMock()
        adapter.apply_domain(query, Item, domain)

        # Should call filter once with an OR expression
        assert query.filter.call_count == 1
        args = query.filter.call_args[0]
        # args[0] is the binary expression.
        # Hard to assert deep internal structure of SA expression without real DB,
        # but verifying it attempts to filter is good enough for adapter logic check.
