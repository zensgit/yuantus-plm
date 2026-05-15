"""Tests for the automation-rule predicate pure-contract (R1).

Covers DTO validation, the evaluator match matrix, workflow_map_id
independence, the fail-open pin (illegal stored match_predicates ->
empty predicate but workflow_map_id preserved), a real service-parity
matrix vs `_rule_matches_runtime_scope`, an AST purity guard, and a
drift guard vs the service constants.
"""

from __future__ import annotations

import ast
import inspect
from unittest.mock import MagicMock

import pytest

# Register ORM mappers (instantiating WorkflowCustomActionRule for the
# parity matrix triggers SQLAlchemy mapper configuration which needs
# Item registered).
from yuantus.meta_engine.models.item import Item  # noqa: F401
from yuantus.meta_engine.models.parallel_tasks import WorkflowCustomActionRule
from yuantus.meta_engine.services import (
    automation_rule_predicate_contract as mod,
)
from yuantus.meta_engine.services.automation_rule_predicate_contract import (
    WorkflowRuleFacts,
    WorkflowRulePredicate,
    evaluate_rule_predicate,
    normalize_workflow_rule_predicate,
)
from yuantus.meta_engine.services.parallel_tasks_service import (
    WorkflowCustomActionService,
)


def _facts(**kw):
    return WorkflowRuleFacts.from_context(kw)


# --------------------------------------------------------------------------
# DTO
# --------------------------------------------------------------------------


def test_predicate_frozen_and_extra_forbid():
    p = WorkflowRulePredicate(eco_priority="high")
    with pytest.raises(Exception):
        p.eco_priority = "low"
    with pytest.raises(ValueError):
        WorkflowRulePredicate(bogus=1)


def test_predicate_rejects_unknown_enum():
    with pytest.raises(ValueError, match="eco_priority must be one of"):
        WorkflowRulePredicate(eco_priority="whenever")
    with pytest.raises(ValueError, match="eco_type must be one of"):
        WorkflowRulePredicate(eco_type="widget")


def test_normalize_dedups_and_lowercases_actor_roles():
    p = normalize_workflow_rule_predicate(
        None, {"actor_roles": ["QA", "qa", " Eng ", "eng"]}
    )
    assert p.actor_roles == ("qa", "eng")


def test_normalize_drops_blank_and_empties():
    p = normalize_workflow_rule_predicate("  ", {"stage_id": "  "})
    assert p.workflow_map_id is None
    assert p.stage_id is None
    assert p.is_empty() is True


def test_facts_normalization_matches_context_rules():
    f = WorkflowRuleFacts.from_context(
        {"eco_priority": "HIGH", "eco_type": "BOM", "actor_roles": ["QA", "qa"]}
    )
    assert f.eco_priority == "high"
    assert f.eco_type == "bom"
    assert f.actor_roles == ("qa",)


# --------------------------------------------------------------------------
# Evaluator matrix
# --------------------------------------------------------------------------


def test_empty_predicate_matches_everything():
    p = normalize_workflow_rule_predicate(None, None)
    assert p.is_empty() is True
    assert evaluate_rule_predicate(p, _facts()) is True
    assert evaluate_rule_predicate(p, _facts(eco_type="bom", stage_id="s1")) is True


@pytest.mark.parametrize(
    "key,pval,good,bad",
    [
        ("stage_id", "s1", {"stage_id": "s1"}, {"stage_id": "s2"}),
        ("eco_priority", "high", {"eco_priority": "high"}, {"eco_priority": "low"}),
        ("product_id", "p1", {"product_id": "p1"}, {"product_id": "p9"}),
        ("eco_type", "bom", {"eco_type": "bom"}, {"eco_type": "document"}),
    ],
)
def test_single_key_truthy_equality(key, pval, good, bad):
    p = normalize_workflow_rule_predicate(None, {key: pval})
    assert evaluate_rule_predicate(p, _facts(**good)) is True
    assert evaluate_rule_predicate(p, _facts(**bad)) is False
    # absent fact for a constrained key -> no match
    assert evaluate_rule_predicate(p, _facts()) is False


def test_actor_roles_intersection_semantics():
    p = normalize_workflow_rule_predicate(None, {"actor_roles": ["qa", "eng"]})
    assert evaluate_rule_predicate(p, _facts(actor_roles=["eng"])) is True
    assert evaluate_rule_predicate(p, _facts(actor_roles=["pm"])) is False
    assert evaluate_rule_predicate(p, _facts()) is False


def test_multi_key_is_and():
    p = normalize_workflow_rule_predicate(
        None, {"eco_type": "bom", "eco_priority": "high"}
    )
    assert evaluate_rule_predicate(p, _facts(eco_type="bom", eco_priority="high")) is True
    assert evaluate_rule_predicate(p, _facts(eco_type="bom", eco_priority="low")) is False


# --------------------------------------------------------------------------
# workflow_map_id independence
# --------------------------------------------------------------------------


def test_workflow_map_id_matches_independently():
    p = normalize_workflow_rule_predicate("wf1", None)
    assert p.is_empty() is False
    assert evaluate_rule_predicate(p, _facts(workflow_map_id="wf1")) is True
    assert evaluate_rule_predicate(p, _facts(workflow_map_id="wf2")) is False
    assert evaluate_rule_predicate(p, _facts()) is False


def test_workflow_map_id_and_predicates_are_anded():
    p = normalize_workflow_rule_predicate("wf1", {"eco_type": "bom"})
    assert evaluate_rule_predicate(
        p, _facts(workflow_map_id="wf1", eco_type="bom")
    ) is True
    assert evaluate_rule_predicate(
        p, _facts(workflow_map_id="wf1", eco_type="document")
    ) is False
    assert evaluate_rule_predicate(
        p, _facts(workflow_map_id="wf2", eco_type="bom")
    ) is False


# --------------------------------------------------------------------------
# Fail-open pin (mirrors _rule_match_predicates line 2169)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_mp",
    [
        {"bogus": 1},  # unsupported key
        {"eco_priority": "whenever"},  # bad enum
        {"eco_type": "widget"},  # bad enum
        {"actor_roles": "qa"},  # non-array
        ["not", "a", "dict"],  # non-dict
    ],
)
def test_fail_open_drops_predicates_but_keeps_workflow_map_id(bad_mp):
    # An illegal stored match_predicates degrades to the empty predicate
    # (match-all) -- this is the CURRENT behavior pinned by R1 (see
    # WorkflowCustomActionService._rule_match_predicates line 2169). It
    # must NOT be hardened in this PR. workflow_map_id (a rule column
    # read before the fail-open path) is preserved.
    with_wf = normalize_workflow_rule_predicate("wfX", bad_mp)
    assert with_wf.workflow_map_id == "wfX"
    assert with_wf.stage_id is None and with_wf.eco_priority is None
    assert with_wf.actor_roles == () and with_wf.product_id is None
    assert with_wf.eco_type is None
    # only workflow_map_id constrains; everything else matches all.
    assert evaluate_rule_predicate(with_wf, _facts(workflow_map_id="wfX")) is True
    assert evaluate_rule_predicate(with_wf, _facts(workflow_map_id="other")) is False

    no_wf = normalize_workflow_rule_predicate(None, bad_mp)
    assert no_wf.is_empty() is True
    assert evaluate_rule_predicate(no_wf, _facts(eco_type="bom")) is True


# --------------------------------------------------------------------------
# Service-parity matrix vs the real _rule_matches_runtime_scope
# --------------------------------------------------------------------------


_PARITY_CASES = [
    # (workflow_map_id, raw_match_predicates, runtime_context)
    (None, None, {}),
    (None, {}, {"eco_type": "bom"}),
    (None, {"eco_type": "bom"}, {"eco_type": "bom"}),
    (None, {"eco_type": "bom"}, {"eco_type": "document"}),
    (None, {"eco_type": "bom"}, {}),
    (None, {"eco_priority": "High"}, {"eco_priority": "high"}),
    (
        None,
        {"actor_roles": ["QA", "Eng"]},
        {"actor_roles": ["eng", "pm"]},
    ),
    (None, {"actor_roles": ["qa"]}, {"actor_roles": ["pm"]}),
    (
        None,
        {"stage_id": "s1", "product_id": "p1"},
        {"stage_id": "s1", "product_id": "p1"},
    ),
    (
        None,
        {"stage_id": "s1", "product_id": "p1"},
        {"stage_id": "s1", "product_id": "p9"},
    ),
    ("wf1", None, {"workflow_map_id": "wf1"}),
    ("wf1", None, {"workflow_map_id": "wf2"}),
    ("wf1", {"eco_type": "bom"}, {"workflow_map_id": "wf1", "eco_type": "bom"}),
    ("wf1", {"eco_type": "bom"}, {"workflow_map_id": "wf2", "eco_type": "bom"}),
    # mixed-case actor_roles on BOTH sides: bit-for-bit lowercasing is
    # load-bearing here (service _normalize_match_predicates +
    # _normalize_runtime_context both lowercase).
    (
        None,
        {"actor_roles": ["QA", "Eng"]},
        {"actor_roles": ["ENG", "Pm"]},
    ),
    (
        None,
        {"actor_roles": ["QA"]},
        {"actor_roles": ["Pm"]},
    ),
    # illegal/fail-open cases
    (None, {"bogus": 1}, {"eco_type": "bom"}),
    ("wfX", {"bogus": 1}, {"eco_type": "bom"}),
    ("wfX", {"bogus": 1}, {"workflow_map_id": "wfX"}),
    (None, {"eco_priority": "nope"}, {"eco_priority": "high"}),
    (None, {"actor_roles": "qa"}, {"actor_roles": ["qa"]}),
]


@pytest.mark.parametrize("wf,mp,ctx", _PARITY_CASES)
def test_service_parity(wf, mp, ctx):
    svc = WorkflowCustomActionService(MagicMock())
    rule = WorkflowCustomActionRule(
        name="parity-rule",
        workflow_map_id=wf,
        action_params=({"match_predicates": mp} if mp is not None else {}),
    )
    service_decision = svc._rule_matches_runtime_scope(
        rule=rule, context=svc._normalize_runtime_context(ctx)
    )
    contract_decision = evaluate_rule_predicate(
        normalize_workflow_rule_predicate(wf, mp),
        WorkflowRuleFacts.from_context(ctx),
    )
    assert service_decision == contract_decision, (
        f"parity drift: wf={wf} mp={mp} ctx={ctx} "
        f"service={service_decision} contract={contract_decision}"
    )


# --------------------------------------------------------------------------
# Purity guard
# --------------------------------------------------------------------------


def test_module_is_pure():
    tree = ast.parse(inspect.getsource(mod))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    joined = " ".join(imported)
    for forbidden in (
        "yuantus.database",
        "sqlalchemy",
        "parallel_tasks_service",
        "WorkflowCustomActionService",
        "_router",
        "plugins",
    ):
        assert forbidden not in joined, f"must stay pure: imports {forbidden!r}"
    # enum domains come from the model layer
    assert "yuantus.meta_engine.models.eco" in joined


# --------------------------------------------------------------------------
# Drift guard vs the live service constants
# --------------------------------------------------------------------------


def test_drift_predicate_key_set_matches_service():
    assert set(mod._ALLOWED_MATCH_PREDICATE_KEYS) == set(
        WorkflowCustomActionService._ALLOWED_MATCH_PREDICATES
    )


def test_drift_enum_domains_match_service():
    assert set(mod._ALLOWED_ECO_PRIORITIES) == set(
        WorkflowCustomActionService._ALLOWED_ECO_PRIORITIES
    )
    assert set(mod._ALLOWED_ECO_TYPES) == set(
        WorkflowCustomActionService._ALLOWED_ECO_TYPES
    )
