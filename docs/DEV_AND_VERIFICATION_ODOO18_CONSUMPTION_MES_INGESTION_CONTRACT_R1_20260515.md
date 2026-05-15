# Odoo18 Consumption MES Ingestion Contract R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement R1 of the consumption ↔ MES ingestion contract taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_CONSUMPTION_MES_INGESTION_CONTRACT_20260515.md`),
candidate #7 from `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §四.8.

R1 is **contract-only and default no-op**: it ships a typed inbound DTO,
a pure mapper into the exact `ConsumptionPlanService.add_actual` keyword
arguments, a deterministic idempotency-key derivation (recorded, not
enforced), and the drift/round-trip tests. Nothing executes unless a test
calls it — there is no route, table, migration, flag, or runtime wiring.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/consumption_mes_contract.py`
- `src/yuantus/meta_engine/tests/test_consumption_mes_ingestion_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_CONSUMPTION_MES_INGESTION_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

No runtime file other than the new module was touched.
`parallel_tasks_service.py`, the consumption router, the ORM models, and
the workorder version-lock R1 paths are **unchanged**.

## 3. Contract

### 3.1 `MesConsumptionEvent` (Pydantic v2, frozen, `extra="forbid"`)

| Field | Type | Required | Validation |
|---|---|---|---|
| `plan_id` | `str` | yes | stripped, non-empty |
| `mes_event_id` | `str` | yes | stripped, non-empty |
| `actual_quantity` | `float` | yes | finite (reject NaN/±inf), `>= 0` |
| `source_type` | `str` (default `mes`) | no | lowercased, must be in `{mes, workorder}` (the MES boundary; `manual` is human entry, not a MES event) |
| `source_id` | `str \| None` | no | blank → `None` |
| `recorded_at` | `datetime \| None` | no | tz-aware → converted to UTC then made naive (column is naive `DateTime`) |
| `uom` | `str \| None` | no | blank → `None`; echoed only, not reconciled |
| `attributes` | `dict` | no | merged into `properties`; must not contain reserved `_ingestion` key |

The model is `frozen=True` so a validated event cannot be mutated between
validation and mapping, and `extra="forbid"` so unknown MES fields fail
fast rather than being silently dropped.

### 3.2 Idempotency key

```
derive_consumption_idempotency_key(event) =
    sha256("{plan_id}\x1f{source_type}\x1f{mes_event_id}").hexdigest()
```

Deterministic across retries of the same event; distinct when any of
`plan_id` / `source_type` / `mes_event_id` differ. **R1 only derives and
records this key** inside `properties["_ingestion"]`. It does **not**
enforce uniqueness — no DB constraint, no dedupe. Enforcement is a
separate, later opt-in (documented as a non-goal in the taskbook §5/§9).

### 3.3 `ConsumptionRecordInputs` + mapper

`map_mes_event_to_consumption_record_inputs(event)` is a **pure** function
(no DB reads). It returns a frozen `ConsumptionRecordInputs` dataclass
whose `as_kwargs()` is exactly the keyword set
`ConsumptionPlanService.add_actual` accepts:
`plan_id, actual_quantity, source_type, source_id, recorded_at, properties`.

`properties` is `dict(event.attributes)` plus a reserved envelope:

```json
{
  "_ingestion": {
    "contract_version": "mes-consumption.v1",
    "idempotency_key": "<sha256 hex>",
    "mes_event_id": "<raw>",
    "source_type": "<normalized>",
    "uom": "<echoed or null>"
  }
}
```

A caller-supplied `attributes` that already contains `_ingestion` is
rejected with `ValueError` so the envelope can never be spoofed. The
mapper does not mutate the input event's `attributes`.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_consumption_mes_ingestion_contract.py`
(test groups below; exact count grows as cases are added):

- **DTO validation**: minimal payload, id stripping, empty-id rejection,
  negative / non-finite quantity rejection, source_type allowlist +
  lowercasing, frozen, `extra=forbid`, tz-aware → naive-UTC conversion,
  blank source_id/uom → None.
- **Idempotency key**: deterministic; differs on each identity field;
  sha256-hex shape.
- **Mapper**: kwargs exactly match the live `add_actual` signature;
  attributes merge + envelope injection; reserved-key collision
  rejection; input not mutated; `recorded_at=None` passthrough.
- **Round-trip**: mapper output fed into the *real*
  `ConsumptionPlanService.add_actual` against in-memory SQLite; the
  persisted row carries the derived idempotency key — proves the
  contract is compatible with the existing write path without modifying
  it.
- **Drift guards** (the core R1 value):
  - `ConsumptionRecordInputs` fields are a subset of
    `ConsumptionRecord.__table__.columns`.
  - `ConsumptionRecordInputs` fields **exactly** equal the `add_actual`
    parameter set (excluding `self` / `**kwargs`). If either the schema
    or the signature drifts, this test fails loudly rather than the
    contract silently rotting.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_consumption_mes_ingestion_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k consumption
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/consumption_mes_contract.py
git diff --check
```

No alembic / tenant-baseline commands — R1 adds no schema.

Observed results as of 2026-05-15 (counts are a point-in-time snapshot
and will grow as cases are added): contract tests all passed; existing
consumption tests all passed; doc-index trio passed; py_compile clean;
`git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §9)

No route; no table / migration / tenant baseline; no DB unique constraint
or dedupe enforcement; no change to `add_actual` or `variance` semantics;
no runtime ingestion wiring; no feature flag / production setting; no uom
reconciliation against the plan; no contact with the workorder
version-lock R1 paths (`eco_service`, `WorkorderDocumentPackService`,
`parallel_tasks_workorder_docs_router`). `.claude/` and `local-dev-env/`
stay out of git.

## 7. Follow-ups (tracked, not in R1)

- Idempotency enforcement: dedupe-on-ingest, which would need either a DB
  unique key or an application-level pre-check. Separate opt-in.
- `uom` reconciliation against `plan.uom` (needs a DB read; out of a pure
  mapper). Separate opt-in.
- Actual ingestion wiring (route / job / connector). Separate opt-in;
  must not double-count given §5's no-enforcement stance.
