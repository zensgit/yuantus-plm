# Odoo18 Quality `is_mandatory` Policy Overlay R1 — Development and Verification

Date: 2026-05-16

## 1. Goal

Implement R1 of the quality `is_mandatory` policy-overlay taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_QUALITY_IS_MANDATORY_POLICY_20260516.md`,
merged `d3c4ad5`) — R2 closeout §4 Tier-A follow-up #2. A **pure
caller-supplied policy overlay** that refines the shipped quality-gate
report into mandatory-blocking vs advisory — **without** touching the
shipped gate, the model, or any runtime.

R1 is **pure, REPORT ONLY, default-preserving**: a module + tests +
this MD. No `is_mandatory` column, no schema, no enforcement, no
runtime, no edit to `quality_workorder_gate_contract`.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/quality_mandatory_policy_contract.py`
- `src/yuantus/meta_engine/tests/test_quality_mandatory_policy_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_QUALITY_MANDATORY_POLICY_CONTRACT_R1_20260516.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`quality_workorder_gate_contract` (the shipped gate, its
`QualityPointDescriptor`, `evaluate_operation_quality_gate`, and its
four MANDATORY tests), the quality models, all services/routers, and
the prior R2 contracts are **unchanged** — proven by an exactly-named
test.

## 3. Contract

- `MandatoryPolicy` — frozen. `from_mapping(Mapping[str,bool])` /
  `empty()`; `is_mandatory(point_id) -> bool`. **Default = mandatory**:
  any point not explicitly `False` is mandatory (explicit `True` ==
  default; only explicit `False` downgrades). Internally stores just
  the explicit non-mandatory id set.
- `MandatoryGateReport` — frozen dataclass: `mandatory_blocked`,
  `advisory_unmet`, `cleared` (passthrough), `mandatory_ok`
  (`len(mandatory_blocked) == 0`).
- `classify_gate_result_by_mandatory(report, policy)` — pure. Takes an
  already-built shipped `OperationQualityGateReport`, partitions its
  `blocked + missing` into `mandatory_blocked` vs `advisory_unmet` by
  the policy (default mandatory), passes `cleared` through. Never
  recomputes/calls the gate, reads a DB, or raises.

### Boundary (owner-scoped, taskbook §3/§8)

`is_mandatory` is a **caller policy overlay**, never a `QualityPoint`
column, never added to the shipped `QualityPointDescriptor` (which
would break #581's column-subset drift guard). The module imports the
shipped `OperationQualityGateReport` **type only** — it does **not**
call `evaluate_operation_quality_gate`. **Default = mandatory ⇒ an
empty policy yields a verdict identical to the shipped gate.**
Report-only: no `assert_*`, no `raise`.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_quality_mandatory_policy_contract.py`
(test groups; counts are a point-in-time snapshot):

- `MandatoryPolicy`: frozen; default-True; explicit-False honoured;
  `empty()`.
- Classification: blocked w/o policy → `mandatory_blocked`;
  `is_mandatory=False` → `advisory_unmet`; all-advisory →
  `mandatory_ok=True` even though `report.ok` is False;
  `cleared` passthrough.
- **`test_default_is_mandatory_preserves_shipped_gate_behavior`
  (MANDATORY, exactly named)** — parametrized over ok/blocked/missing/
  mixed shipped reports: empty policy ⇒ every blocked/missing is
  `mandatory_blocked`, `advisory_unmet` empty, and
  `mandatory_ok == report.ok` (taskbook §3.2 pinned).
- **`test_is_mandatory_is_descriptor_only_no_schema_no_runtime`
  (MANDATORY, exactly named)** — (a) `QualityPoint` has no
  `is_mandatory` column; (b) shipped `QualityPointDescriptor` has no
  `is_mandatory` field; (c) AST: module imports nothing from
  `yuantus.database`/`sqlalchemy`/router/`plugins`, contains no
  `raise`, and does **not** call `evaluate_operation_quality_gate`.
- **`test_shipped_gate_contract_is_untouched` (MANDATORY, exactly
  named)** — `QualityPointDescriptor.model_fields` is exactly the
  merged #581 set; the four MANDATORY shipped-gate test names still
  exist verbatim in `test_quality_workorder_gate_contract.py`.
- `test_no_assert_callable_in_module` — no `assert_*` callable
  (report-only).

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_quality_mandatory_policy_contract.py \
  src/yuantus/meta_engine/tests/test_quality_workorder_gate_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/quality_mandatory_policy_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

Observed as of 2026-05-16: policy contract tests passed; shipped
quality-gate regression passed (unchanged); doc-index trio + R2
portfolio drift guard passed; py_compile clean; `git diff --check`
clean.

## 6. Non-Goals (reaffirmed from taskbook §8)

No `is_mandatory` column / schema / migration / tenant-baseline; no
edit to `quality_workorder_gate_contract` (descriptor, gate, or its
four MANDATORY tests); no enforcement / `assert_*` / raiser; no wiring
/ runtime / DB read / feature flag. Only the shipped
`OperationQualityGateReport` **type** is imported. `.claude/` and
`local-dev-env/` stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- `assert_mandatory_clear(...)` enforcement seam (still pure; separate
  so report-vs-enforce stays a conscious choice).
- Modelling `is_mandatory` as a real `QualityPoint` column (schema).
- Wiring the classification into a gate caller (depends on the
  non-existent workorder-execution domain — Tier C).
