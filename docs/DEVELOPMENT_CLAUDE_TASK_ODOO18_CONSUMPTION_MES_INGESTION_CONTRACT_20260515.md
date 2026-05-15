# Claude Taskbook: Odoo18 Consumption Plan ↔ MES Ingestion Contract R1

Date: 2026-05-15

## 1. Purpose

Define a typed, validated **ingestion contract** between an external MES
(Manufacturing Execution System) and the existing `ConsumptionRecord`
store, so that a future MES connector has a stable, drift-checked boundary
to target.

This is candidate #7 from `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`
§四.8. It was picked first because it is the only R2 candidate that is, by
construction, **default no-op**: it adds no route, no table, no production
switch, and does not touch the workorder version-lock R1 runtime path
(`12456d3`).

R1 is **contract-only**. It delivers a Pydantic DTO + a pure
mapper/validator + a deterministic idempotency-key derivation + drift
tests. It does **not** wire any runtime ingestion. Wiring (a route, a job,
or a connector) is a separate, later opt-in.

This taskbook is implementation-facing but is itself **doc-only**. The
implementation PR happens only after this taskbook is reviewed and merged,
and after a separate explicit opt-in.

## 2. Current Baseline

Code evidence (read before implementing):

- `src/yuantus/meta_engine/models/parallel_tasks.py` defines
  `ConsumptionPlan` (`meta_consumption_plans`) and `ConsumptionRecord`
  (`meta_consumption_records`). `ConsumptionRecord` columns today:
  - `id` (str, pk)
  - `plan_id` (str, indexed, not null)
  - `source_type` (str, default `"workorder"`)
  - `source_id` (str, nullable, indexed)
  - `actual_quantity` (float, default 0.0)
  - `recorded_at` (datetime, default now, indexed)
  - `properties` (JSON/JSONB, nullable)
  - **No unique constraint** beyond the primary key. There is no
    idempotency / dedupe key in the schema today.
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  `ConsumptionPlanService.add_actual(...)` is the single existing write
  path. Signature: `plan_id, actual_quantity, source_type="workorder",
  source_id=None, recorded_at=None, properties=None`. It validates the
  plan exists, lowercases `source_type`, and inserts one row. It does
  **not** dedupe.
- `ConsumptionPlanService.variance(plan_id)` sums every record for a plan
  (`actual_total = sum(record.actual_quantity)`), so duplicate inserts
  today would double-count.
- `src/yuantus/meta_engine/web/parallel_tasks_consumption_router.py`
  already exposes `POST /consumption/plans/{plan_id}/actuals`
  (`add_consumption_actual`) backed by `add_actual`. This route is
  generic; it is **not** the MES ingestion contract and must not be
  modified in R1.

Implication: today an MES could already POST to `/actuals`, but there is
no typed contract, no field mapping discipline, and no replay protection —
a retried MES delivery would double-count in `variance`. R1 closes the
contract gap without changing any of the above runtime behavior.

## 3. R1 Target Output

One bounded, doc-reviewed implementation PR (authored later, separate
opt-in) delivering:

- A Pydantic v2 DTO `MesConsumptionEvent` describing the inbound MES
  payload.
- A pure function `map_mes_event_to_consumption_record_inputs(event)
  -> ConsumptionRecordInputs` that validates and maps the DTO to the
  exact kwargs `add_actual` already accepts (plus a derived idempotency
  key carried inside `properties`).
- A deterministic idempotency-key derivation
  `derive_consumption_idempotency_key(event) -> str`.
- Drift tests asserting the DTO/mapper stay aligned with the live
  `ConsumptionRecord` columns and `add_actual` signature.

No route, no table, no migration, no production switch, no change to
`add_actual` / `variance` semantics.

## 4. Ingestion Payload Contract

Proposed `MesConsumptionEvent` (Pydantic v2, frozen):

| Field | Type | Required | Notes |
|---|---|---|---|
| `plan_id` | `str` | yes | Target consumption plan id |
| `mes_event_id` | `str` | yes | The MES system's own event/transaction id; the basis of idempotency |
| `actual_quantity` | `float` | yes | Non-negative; `>= 0` validator |
| `source_type` | `str` | no (default `"mes"`) | Lowercased; constrained to a small allowlist (see §6) |
| `source_id` | `str \| None` | no | MES work order / lot id; free-form |
| `recorded_at` | `datetime \| None` | no | If absent, mapper leaves it None so `add_actual` applies its own default |
| `uom` | `str \| None` | no | Carried for validation only in R1 (see §6); not written to a column |
| `attributes` | `dict[str, Any]` | no | Arbitrary MES context; flows into `properties` under a namespaced key |

Validation rules to specify in the taskbook (enforced by the DTO):

- `plan_id` and `mes_event_id` non-empty after strip.
- `actual_quantity` is finite and `>= 0` (reject NaN/inf/negative).
- `source_type` lowercased, must be in the allowlist.
- `recorded_at` if present must be timezone-aware or explicitly
  documented as naive-UTC; pick one and assert it in tests.

## 5. Idempotency Key

R1 does **not** add a DB unique constraint (that would be a schema change
and a separate opt-in). Instead the contract defines a deterministic key
that a future ingestion wiring can use to dedupe before calling
`add_actual`:

```
derive_consumption_idempotency_key(event) =
    sha256(f"{plan_id}\x1f{source_type}\x1f{mes_event_id}").hexdigest()
```

The mapper writes this key into `properties` under a reserved namespace,
e.g. `properties["_ingestion"] = {"idempotency_key": "<hex>",
"mes_event_id": "<raw>", "contract_version": "mes-consumption.v1"}`.

The taskbook must state explicitly:

- R1 only *derives and records* the key. It does **not** enforce
  uniqueness. Dedupe enforcement is deferred to the wiring PR and
  documented as a non-goal here.
- The key is stable across retries of the same MES event and distinct
  across different plans/sources.

## 6. Field Mapping

`map_mes_event_to_consumption_record_inputs` returns a typed
`ConsumptionRecordInputs` (a small dataclass / TypedDict) carrying exactly:

| Target (`add_actual` kwarg) | Source | Rule |
|---|---|---|
| `plan_id` | `event.plan_id` | passthrough |
| `actual_quantity` | `event.actual_quantity` | `float(...)`, already validated `>= 0` |
| `source_type` | `event.source_type` | lowercased; default `"mes"` |
| `source_id` | `event.source_id` | passthrough (may be None) |
| `recorded_at` | `event.recorded_at` | passthrough (None lets `add_actual` default) |
| `properties` | `event.attributes` + ingestion envelope | merge: `{**attributes, "_ingestion": {...}}`; reject if caller-supplied `attributes` already contains reserved `_ingestion` key |

`uom`: in R1 the contract validates `uom` against `plan.uom` is **out of
scope** (it would require a DB read inside a pure mapper). The taskbook
should specify that `uom` is accepted, echoed into the ingestion envelope
for observability, but **not** reconciled against the plan in R1; uom
reconciliation is a documented follow-up.

## 7. Tests Required (to be written in the implementation PR)

Contract / unit tests (new file, e.g.
`test_consumption_mes_ingestion_contract.py`):

- DTO accepts a minimal valid payload.
- DTO rejects: empty `plan_id`, empty `mes_event_id`, negative quantity,
  NaN/inf quantity, `source_type` outside allowlist.
- `derive_consumption_idempotency_key` is deterministic for identical
  input and differs when `plan_id` / `source_type` / `mes_event_id`
  differ.
- Mapper output kwargs are exactly the set `add_actual` accepts (no
  extra/missing keys).
- Mapper merges `attributes` into `properties` and injects the
  `_ingestion` envelope; rejects reserved-key collision.
- Round-trip: feeding the mapper output into a real
  `ConsumptionPlanService.add_actual(...)` against an in-memory SQLite
  session persists a row whose `properties["_ingestion"]["idempotency_key"]`
  equals the derived key (proves the contract is compatible with the
  existing write path without modifying it).

Drift test (the core value of R1):

- A test that introspects `ConsumptionRecord.__table__.columns` and the
  `add_actual` signature and asserts the mapper targets stay a subset of
  both. If a future schema/signature change drifts, this test fails
  loudly rather than the contract silently rotting.

Doc-index trio must stay green for the new DEV/verification MD added by
the implementation PR.

## 8. Verification Commands (for the implementation PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_consumption_mes_ingestion_contract.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/parallel_tasks_service.py
git diff --check
```

No alembic / tenant-baseline commands: R1 adds no schema.

## 9. Non-Goals (hard boundaries)

- **No new route.** Do not add an MES ingestion endpoint. Do not modify
  `POST /consumption/plans/{plan_id}/actuals`.
- **No new table and no migration.** `ConsumptionRecord` schema is
  untouched.
- **No DB unique constraint / no dedupe enforcement.** R1 only derives
  and records the idempotency key.
- **No change to `add_actual` or `variance` semantics.** The contract
  must be compatible with them as-is, proven by the round-trip test.
- **No runtime ingestion wiring** (no job, no connector, no scheduler).
- **No production setting / feature flag.** Nothing in R1 executes unless
  a test calls it.
- **No uom reconciliation against the plan.** Accepted and echoed only.
- **No touch to workorder version-lock R1 paths** (`eco_service`,
  `WorkorderDocumentPackService`, `parallel_tasks_workorder_docs_router`).

## 10. Claude Code Handoff

Claude Code should own the implementation PR **after this taskbook is
merged and after a separate explicit opt-in**.

Suggested implementation branch:

`feat/odoo18-consumption-mes-ingestion-contract-r1-20260515`

Claude Code should:

- Read this taskbook and `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`.
- Implement only the contract: DTO + pure mapper + key derivation +
  tests + a DEV/verification MD.
- Add no route, no table, no migration, no flag.
- Keep `.claude/` and `local-dev-env/` out of git.
- Stop and report if the mapper cannot be kept pure (no DB reads) while
  satisfying the contract.

Reviewer focus (per the owner):

- Did anything smuggle in runtime ingestion (route / job / connector)?
- Did `ConsumptionRecord` semantics or `add_actual` / `variance` change?
- Is the drift test present and actually asserting column/signature
  alignment (not a tautology)?
- Is the idempotency key deterministic and is its non-enforcement
  clearly documented?
