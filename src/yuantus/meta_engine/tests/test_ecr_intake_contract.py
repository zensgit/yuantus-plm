"""Tests for the ECR intake contract (R1).

Pure-contract coverage: intake validation incl. unknown-enum fail-fast,
the bom⇒product_id boundary invariant, tz-aware→naive-UTC, reference
determinism, mapper exactness vs the real create_eco signature,
user_id=None preservation, a purity guard, and drift guards introspecting
the real ECO enums + create_eco signature.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from yuantus.meta_engine.models.eco import ECOPriority, ECOType
from yuantus.meta_engine.services import ecr_intake_contract as mod
from yuantus.meta_engine.services.ecr_intake_contract import (
    CONTRACT_VERSION,
    ChangeRequestIntake,
    EcoDraftInputs,
    derive_change_request_reference,
    map_change_request_to_eco_draft_inputs,
)
from yuantus.meta_engine.services.eco_service import ECOService


def _intake(**over):
    base = dict(title="Fix bracket", change_type="document")
    base.update(over)
    return ChangeRequestIntake(**base)


# --------------------------------------------------------------------------
# Intake validation
# --------------------------------------------------------------------------


def test_minimal_valid_intake():
    i = _intake()
    assert i.title == "Fix bracket"
    assert i.change_type == "document"
    assert i.priority == "normal"  # default
    assert i.product_id is None
    assert i.requester_user_id is None
    assert i.effectivity_date is None


def test_title_stripped_and_required():
    assert _intake(title="  T  ").title == "T"
    with pytest.raises(ValueError, match="title must be a non-empty"):
        _intake(title="   ")


def test_change_type_normalized_and_validated():
    assert _intake(change_type="DOCUMENT").change_type == "document"
    with pytest.raises(ValueError, match="change_type must be one of"):
        _intake(change_type="widget")


def test_priority_default_and_validation():
    assert _intake().priority == "normal"
    assert _intake(priority="URGENT").priority == "urgent"
    with pytest.raises(ValueError, match="priority must be one of"):
        _intake(priority="whenever")


def test_bom_requires_product_id_at_intake_boundary():
    # Mirrors ECOService.create_eco's own invariant; fail early/clear.
    with pytest.raises(ValueError, match="product_id is required"):
        _intake(change_type="bom")
    # Non-bom types do not require product_id.
    assert _intake(change_type="product").product_id is None
    assert _intake(change_type="document").product_id is None
    # bom WITH product_id is fine.
    assert _intake(change_type="bom", product_id="p1").product_id == "p1"


def test_blank_product_id_and_reason_become_none():
    i = _intake(product_id="  ", reason="  ")
    assert i.product_id is None
    assert i.reason is None


def test_effectivity_date_tzaware_normalized_to_naive_utc():
    aware = datetime(2026, 5, 15, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    i = _intake(effectivity_date=aware)
    assert i.effectivity_date.tzinfo is None
    assert i.effectivity_date == datetime(2026, 5, 15, 4, 0)  # 12:00+08 == 04:00Z


def test_intake_is_frozen_and_forbids_extra():
    i = _intake()
    with pytest.raises(Exception):
        i.title = "other"
    with pytest.raises(ValueError):
        ChangeRequestIntake(title="t", change_type="document", bogus=1)


# --------------------------------------------------------------------------
# Reference
# --------------------------------------------------------------------------


def test_reference_is_deterministic_and_normalisation_stable():
    a = _intake(title=" Fix ", change_type="BOM", product_id="p1")
    b = _intake(title="Fix", change_type="bom", product_id="p1")
    assert derive_change_request_reference(a) == derive_change_request_reference(b)


@pytest.mark.parametrize(
    "over",
    [
        {"title": "Other"},
        {"change_type": "product"},
        {"product_id": "p2"},
        {"requester_user_id": 9},
    ],
)
def test_reference_differs_on_stable_fields(over):
    base_kwargs = dict(
        title="Fix bracket",
        change_type="document",
        product_id="p1",
        requester_user_id=1,
    )
    base = _intake(**base_kwargs)
    other = _intake(**{**base_kwargs, **over})
    assert derive_change_request_reference(base) != derive_change_request_reference(
        other
    )


def test_reference_is_sha256_hex():
    r = derive_change_request_reference(_intake())
    assert len(r) == 64
    int(r, 16)


# --------------------------------------------------------------------------
# Mapper
# --------------------------------------------------------------------------


def test_mapper_kwargs_exactly_match_create_eco_signature():
    inputs = map_change_request_to_eco_draft_inputs(_intake())
    produced = set(inputs.as_kwargs().keys())
    sig = inspect.signature(ECOService.create_eco)
    accepted = {
        n
        for n, p in sig.parameters.items()
        if n != "self" and p.kind != inspect.Parameter.VAR_KEYWORD
    }
    assert produced == accepted


def test_mapper_output_binds_to_create_eco_without_calling_it():
    # Shape compatibility proven WITHOUT invoking create_eco (no DB).
    inputs = map_change_request_to_eco_draft_inputs(
        _intake(change_type="bom", product_id="p1", requester_user_id=None)
    )
    sig = inspect.signature(ECOService.create_eco)
    # Binds with user_id=None; create_eco normalizes falsy user_id to 1
    # internally, so None is correct and the 1:1 mapping holds.
    bound = sig.bind(ECOService, **inputs.as_kwargs())
    assert bound.arguments["user_id"] is None


def test_mapper_preserves_user_id_none():
    inputs = map_change_request_to_eco_draft_inputs(
        _intake(requester_user_id=None)
    )
    assert inputs.user_id is None
    inputs2 = map_change_request_to_eco_draft_inputs(
        _intake(requester_user_id=7)
    )
    assert inputs2.user_id == 7


def test_mapper_composes_description_envelope():
    with_reason = map_change_request_to_eco_draft_inputs(
        _intake(reason="cracked under load")
    )
    assert with_reason.description.startswith("cracked under load")
    assert CONTRACT_VERSION in with_reason.description
    assert derive_change_request_reference(_intake(reason="cracked under load")) in (
        with_reason.description
    )
    no_reason = map_change_request_to_eco_draft_inputs(_intake())
    assert no_reason.description.startswith("[ecr-intake")


def test_mapper_does_not_mutate_intake():
    i = _intake(reason="r")
    map_change_request_to_eco_draft_inputs(i)
    assert i.reason == "r"
    assert i.title == "Fix bracket"


# --------------------------------------------------------------------------
# Purity guard
# --------------------------------------------------------------------------


def test_module_has_no_forbidden_imports():
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
        "eco_service",
        "change_service",
        "_router",
        "plugins",
    ):
        assert forbidden not in joined, (
            f"contract must stay pure: imports {forbidden!r}"
        )
    # It MAY (and must, for the drift guard) import the ECO enums.
    assert "yuantus.meta_engine.models.eco" in joined


def test_module_does_not_call_create_eco():
    # AST (not substring): the module may *mention* create_eco in
    # docstrings/comments; it must never *call* it.
    tree = ast.parse(inspect.getsource(mod))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "attr", None) or getattr(fn, "id", None)
            assert name != "create_eco", "R1 must not invoke create_eco"


# --------------------------------------------------------------------------
# Drift guards
# --------------------------------------------------------------------------


def test_change_type_domain_tracks_real_eco_type_enum():
    assert set(mod._ECO_TYPE_VALUES) == {t.value for t in ECOType}


def test_priority_domain_tracks_real_eco_priority_enum():
    assert set(mod._ECO_PRIORITY_VALUES) == {p.value for p in ECOPriority}


def test_eco_draft_inputs_fields_match_create_eco_params():
    sig = inspect.signature(ECOService.create_eco)
    accepted = {
        n
        for n, p in sig.parameters.items()
        if n != "self" and p.kind != inspect.Parameter.VAR_KEYWORD
    }
    fields = set(EcoDraftInputs.__dataclass_fields__.keys())
    assert fields == accepted, (
        "EcoDraftInputs drifted from create_eco signature: "
        f"missing={accepted - fields} extra={fields - accepted}"
    )


def test_bom_product_id_invariant_constant_matches_enum():
    assert mod._PRODUCT_ID_REQUIRED_FOR == ECOType.BOM.value
