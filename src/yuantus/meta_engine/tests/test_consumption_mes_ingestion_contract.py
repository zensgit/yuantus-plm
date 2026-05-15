"""Contract tests for the MES -> ConsumptionRecord ingestion boundary.

Covers DTO validation, idempotency-key determinism, mapper exactness,
the attributes/_ingestion merge, a round-trip against the real
`ConsumptionPlanService.add_actual`, and a drift test that fails loudly
if `ConsumptionRecord` columns or the `add_actual` signature change out
from under the contract.
"""

from __future__ import annotations

import inspect
import math
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.models.item import Item  # noqa: F401  (mapper registration)
from yuantus.meta_engine.models.parallel_tasks import (
    ConsumptionPlan,
    ConsumptionRecord,
)
from yuantus.meta_engine.services.consumption_mes_contract import (
    ALLOWED_SOURCE_TYPES,
    CONTRACT_VERSION,
    RESERVED_PROPERTIES_KEY,
    ConsumptionRecordInputs,
    MesConsumptionEvent,
    derive_consumption_idempotency_key,
    map_mes_event_to_consumption_record_inputs,
)
from yuantus.meta_engine.services.parallel_tasks_service import (
    ConsumptionPlanService,
)
from yuantus.models.base import Base
from yuantus.security.rbac.models import RBACUser


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            RBACUser.__table__,
            ConsumptionPlan.__table__,
            ConsumptionRecord.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _event(**overrides):
    base = dict(
        plan_id="plan-1",
        mes_event_id="evt-1",
        actual_quantity=5.0,
    )
    base.update(overrides)
    return MesConsumptionEvent(**base)


# --------------------------------------------------------------------------
# DTO validation
# --------------------------------------------------------------------------


def test_dto_accepts_minimal_valid_payload():
    event = _event()
    assert event.plan_id == "plan-1"
    assert event.mes_event_id == "evt-1"
    assert event.actual_quantity == 5.0
    assert event.source_type == "mes"
    assert event.source_id is None
    assert event.recorded_at is None
    assert event.attributes == {}


def test_dto_strips_plan_and_event_ids():
    event = _event(plan_id="  plan-x  ", mes_event_id="  evt-x  ")
    assert event.plan_id == "plan-x"
    assert event.mes_event_id == "evt-x"


@pytest.mark.parametrize("field", ["plan_id", "mes_event_id"])
def test_dto_rejects_empty_ids(field):
    with pytest.raises(ValueError, match="non-empty"):
        _event(**{field: "   "})


def test_dto_rejects_negative_quantity():
    with pytest.raises(ValueError, match=">= 0"):
        _event(actual_quantity=-0.01)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_dto_rejects_non_finite_quantity(bad):
    with pytest.raises(ValueError, match="finite"):
        _event(actual_quantity=bad)


def test_dto_rejects_source_type_outside_allowlist():
    with pytest.raises(ValueError, match="source_type must be one of"):
        _event(source_type="erp")


def test_dto_lowercases_source_type():
    assert _event(source_type="WorkOrder").source_type == "workorder"


def test_dto_is_frozen():
    event = _event()
    with pytest.raises(Exception):
        event.actual_quantity = 9.0


def test_dto_forbids_unknown_fields():
    with pytest.raises(ValueError):
        MesConsumptionEvent(
            plan_id="p", mes_event_id="e", actual_quantity=1.0, bogus=1
        )


def test_dto_normalizes_tzaware_recorded_at_to_naive_utc():
    aware = datetime(2026, 5, 15, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    event = _event(recorded_at=aware)
    assert event.recorded_at.tzinfo is None
    # 12:00 +08:00 == 04:00 UTC
    assert event.recorded_at == datetime(2026, 5, 15, 4, 0)


def test_dto_blank_source_id_and_uom_become_none():
    event = _event(source_id="  ", uom="  ")
    assert event.source_id is None
    assert event.uom is None


# --------------------------------------------------------------------------
# Idempotency key
# --------------------------------------------------------------------------


def test_idempotency_key_is_deterministic():
    e1 = _event()
    e2 = _event()
    assert derive_consumption_idempotency_key(e1) == derive_consumption_idempotency_key(e2)


@pytest.mark.parametrize(
    "overrides",
    [
        {"plan_id": "plan-2"},
        {"source_type": "workorder"},
        {"mes_event_id": "evt-2"},
    ],
)
def test_idempotency_key_differs_on_identity_fields(overrides):
    base_key = derive_consumption_idempotency_key(_event())
    other_key = derive_consumption_idempotency_key(_event(**overrides))
    assert base_key != other_key


def test_idempotency_key_is_sha256_hex():
    key = derive_consumption_idempotency_key(_event())
    assert len(key) == 64
    int(key, 16)  # hex-decodable


# --------------------------------------------------------------------------
# Mapper
# --------------------------------------------------------------------------


def test_mapper_kwargs_exactly_match_add_actual_signature():
    inputs = map_mes_event_to_consumption_record_inputs(_event())
    produced = set(inputs.as_kwargs().keys())

    sig = inspect.signature(ConsumptionPlanService.add_actual)
    accepted = {
        name
        for name, p in sig.parameters.items()
        if name != "self" and p.kind != inspect.Parameter.VAR_KEYWORD
    }
    assert produced == accepted


def test_mapper_merges_attributes_and_injects_envelope():
    event = _event(attributes={"lot": "L-9", "shift": "B"}, uom="EA")
    inputs = map_mes_event_to_consumption_record_inputs(event)

    assert inputs.properties["lot"] == "L-9"
    assert inputs.properties["shift"] == "B"
    envelope = inputs.properties[RESERVED_PROPERTIES_KEY]
    assert envelope["contract_version"] == CONTRACT_VERSION
    assert envelope["idempotency_key"] == derive_consumption_idempotency_key(event)
    assert envelope["mes_event_id"] == "evt-1"
    assert envelope["source_type"] == "mes"
    assert envelope["uom"] == "EA"


def test_mapper_rejects_reserved_key_collision():
    event = _event(attributes={RESERVED_PROPERTIES_KEY: {"spoof": True}})
    with pytest.raises(ValueError, match="reserved key"):
        map_mes_event_to_consumption_record_inputs(event)


def test_mapper_does_not_mutate_event_attributes():
    original = {"lot": "L-1"}
    event = _event(attributes=original)
    map_mes_event_to_consumption_record_inputs(event)
    assert original == {"lot": "L-1"}
    assert RESERVED_PROPERTIES_KEY not in original


def test_mapper_passes_recorded_at_none_through():
    inputs = map_mes_event_to_consumption_record_inputs(_event())
    assert inputs.recorded_at is None


# --------------------------------------------------------------------------
# Round-trip against the real add_actual (no add_actual change)
# --------------------------------------------------------------------------


def test_round_trip_through_real_add_actual(session):
    service = ConsumptionPlanService(session)
    plan = service.create_plan(name="P", item_id="item-1", planned_quantity=10.0)
    session.commit()

    event = _event(
        plan_id=plan.id,
        mes_event_id="evt-rt-1",
        actual_quantity=4.0,
        attributes={"lot": "L-RT"},
    )
    inputs = map_mes_event_to_consumption_record_inputs(event)
    record = service.add_actual(**inputs.as_kwargs())
    session.commit()

    persisted = session.get(ConsumptionRecord, record.id)
    assert persisted.plan_id == plan.id
    assert persisted.actual_quantity == 4.0
    assert persisted.source_type == "mes"
    assert persisted.properties["lot"] == "L-RT"
    assert (
        persisted.properties[RESERVED_PROPERTIES_KEY]["idempotency_key"]
        == derive_consumption_idempotency_key(event)
    )


# --------------------------------------------------------------------------
# Drift guard — the core value of R1
# --------------------------------------------------------------------------


def test_drift_inputs_fields_are_subset_of_consumption_record_columns():
    column_names = {c.name for c in ConsumptionRecord.__table__.columns}
    dataclass_fields = set(ConsumptionRecordInputs.__dataclass_fields__.keys())
    # Every mapper-target field must correspond to a real column. `id` and
    # `recorded_at`/`properties` defaults are handled by add_actual; the
    # contract never targets a column that does not exist.
    assert dataclass_fields <= column_names, (
        f"contract targets columns that no longer exist: "
        f"{dataclass_fields - column_names}"
    )


def test_drift_inputs_fields_exactly_match_add_actual_params():
    sig = inspect.signature(ConsumptionPlanService.add_actual)
    accepted = {
        name
        for name, p in sig.parameters.items()
        if name != "self" and p.kind != inspect.Parameter.VAR_KEYWORD
    }
    dataclass_fields = set(ConsumptionRecordInputs.__dataclass_fields__.keys())
    assert dataclass_fields == accepted, (
        "ConsumptionRecordInputs drifted from add_actual signature: "
        f"missing={accepted - dataclass_fields} "
        f"extra={dataclass_fields - accepted}"
    )


def test_allowlist_is_the_mes_boundary():
    assert ALLOWED_SOURCE_TYPES == {"mes", "workorder"}
    # "manual" is human entry, not a MES event — must be rejected.
    with pytest.raises(ValueError, match="source_type must be one of"):
        _event(source_type="manual")


def test_default_attributes_are_isolated_per_instance():
    a = _event()
    b = _event()
    assert a.attributes == {}
    assert a.attributes is not b.attributes
