# Odoo18 Quality ↔ Workorder Gate Contract R1 — Development and Verification

Date: 2026-05-16

## 1. Goal

Implement R1 of the quality↔workorder runtime gate taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_QUALITY_WORKORDER_RUNTIME_CONTRACT_20260515.md`,
merged `b3f6671`). A **pure** decision — "is this operation
quality-clear?" — over caller-supplied descriptors, activating the
dormant `QualityPoint.trigger_on == "production"` semantics.

R1 is **pure, parallel, default-OFF, behavior-preserving**: a module +
tests + this MD. No service/router/schema/runtime change.

### Honest scope (recorded, not papered over)

Per taskbook §2: `QualityPoint.trigger_on` is consumed **nowhere**;
there is **no operation/workorder execution runtime** (`Operation` has
no lifecycle, `manufacturing_router` is CRUD+release only); QualityPoint
has **no mandatory flag**. So R1 is a pure gate + a default-OFF seam
(`assert_operation_quality_clear`) that **nothing calls** — merging it
changes no behavior. True runtime enforcement is doubly gated on a
workorder-execution domain that does not exist (separate opt-ins).

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/quality_workorder_gate_contract.py`
- `src/yuantus/meta_engine/tests/test_quality_workorder_gate_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_QUALITY_WORKORDER_GATE_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`QualityService`, the quality/manufacturing models, manufacturing
services, all routers, and the prior seven Odoo18 contracts are
**unchanged**.

## 3. Contract

### 3.1 DTOs (Pydantic v2, frozen, `extra="forbid"`)

- `OperationQualityFacts` — the caller-resolved operation context:
  `product_id`, `item_type_id`, `routing_id`, `operation_id` (all
  optional, blank→None).
- `QualityPointDescriptor` — `id` (non-empty), `trigger_on`,
  `is_active`, **four** scope fields (`product_id`, `item_type_id`,
  `routing_id`, `operation_id`). Mirrors `QualityPoint`.
- `QualityCheckDescriptor` — `point_id` (non-empty), `result`
  (validated against the live `QualityCheckResult` domain), **three**
  scope fields (`product_id`, `routing_id`, `operation_id`). Mirrors
  `QualityCheck` — which has **no `item_type_id`**; that asymmetry is
  modeled honestly and pinned by a drift test.

### 3.2 Scope-match rule (§4.1)

For each scope field: descriptor `None` = **wildcard** (matches); a
non-`None` value must **equal** the corresponding `facts` field. Points
use all four fields; checks use their three.

### 3.3 Pure functions

- `resolve_applicable_quality_points(facts, points)` — points that are
  `is_active` **and** `trigger_on == "production"` **and** whose
  four-field scope matches `facts`.
- `evaluate_operation_quality_gate(facts, points, checks)
  -> OperationQualityGateReport` — pure, never raises. **RATIFIED §3**:
  a point is *cleared* iff a check exists with
  `point_id == point.id` **AND** `result == "pass"` **AND** the check's
  three-field scope matches `facts`. A point with only
  `fail`/`warning`/`none` scope-matching checks → `blocked`; with no
  scope-matching check → `missing`. `ok` iff `blocked` and `missing`
  are both empty. The per-check scope filter prevents a
  cross-product/routing/operation `pass` from clearing the wrong point.
- `assert_operation_quality_clear(facts, points, checks)` — the
  **default-OFF seam**: raises `ValueError` listing blocked+missing
  point ids when not `ok`; `None` when clear. Nothing calls it.

### 3.4 RATIFIED §3 policy (binding)

Only `pass` clears. `fail` / `warning` / `none` / missing block.
**`warning` does NOT clear** (owner-ratified conservative policy).

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_quality_workorder_gate_contract.py`
(test groups; counts are a point-in-time snapshot and grow as cases are
added):

- DTO validation: frozen, `extra=forbid`, non-empty `id`/`point_id`,
  `result` ∈ `QualityCheckResult`.
- **`test_point_four_field_scope_wildcard_and_equality` (MANDATORY,
  exactly named)** — pins §4.1 for points: all-None wildcard; a
  mismatch on **any** of the four fields excludes the point; exact
  four-field match applies.
- **`test_cross_scope_pass_check_does_not_clear` (MANDATORY, exactly
  named)** — a `pass` check for the same `point_id` but a different
  `product_id`/`routing_id`/`operation_id` does NOT clear; a `pass`
  for a different `point_id` does NOT clear; the correctly-scoped
  `pass` does clear.
- **`test_only_production_trigger_points_gate_the_operation`
  (MANDATORY, exactly named)** — `manual`/`receipt`/`transfer` and
  inactive points never gate (`total == 0`, `ok`).
- **`test_pass_clears_fail_warning_none_block_by_ratified_policy`
  (MANDATORY, exactly named)** — `pass` clears; `fail`/`warning`/
  `none`/missing block; **`warning` does NOT clear**; comment cites §3.
- Gate basics: empty applicable set → `ok`; seam raises / returns
  `None`.
- **Purity guard**: AST import scan — module imports nothing from
  `yuantus.database` / `sqlalchemy` / `quality.service` /
  `manufacturing` / a router / `plugins`; imports only
  `yuantus.meta_engine.quality.models`.
- **Drift guards**: `QualityPointDescriptor` fields ⊆ `QualityPoint`
  columns; `QualityCheckDescriptor` fields ⊆ `QualityCheck` columns
  (and `item_type_id ∉` `QualityCheck` — the honest asymmetry pinned);
  `_RESULT_VALUES == QualityCheckResult` values and
  `_CLEARING_RESULT == "pass"`; a source-level guard that
  `QualityService.create_point` still validates `"production"` in its
  `trigger_on` set (so a vocab change fails loudly here).

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_quality_workorder_gate_contract.py \
  src/yuantus/meta_engine/tests/test_quality_service.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/quality_workorder_gate_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

Observed as of 2026-05-16: contract tests all passed; quality-service
regression all passed (no regression); doc-index trio passed;
py_compile clean; `git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §8)

No operation/workorder execution runtime; no seam wiring; no setting;
no edit to `QualityService` / quality / manufacturing models /
manufacturing services / any router; no `is_mandatory` column / schema
/ migration / tenant-baseline; no DB read in the contract; no feature
flag; no `eval`; no data migration. No contact with the prior seven
Odoo18 contracts. `.claude/` and `local-dev-env/` stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- **Workorder-execution domain** (operation start/complete lifecycle) —
  prerequisite for any real runtime enforcement; does not exist today.
- **Gate wiring**: a future operation-completion path calling
  `assert_operation_quality_clear` (depends on the above).
- **`is_mandatory` modelling** if per-point blocking granularity is
  later wanted (schema change).
