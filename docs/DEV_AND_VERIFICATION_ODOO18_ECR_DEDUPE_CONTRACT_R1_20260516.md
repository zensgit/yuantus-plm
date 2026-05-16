# Odoo18 ECR Dedupe Pure-Contract R1 — Development and Verification

Date: 2026-05-16

## 1. Goal

Implement R1 of the ECR dedupe taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_ECR_DEDUPE_CONTRACT_20260516.md`,
merged `aa8fdca`) — the R2 closeout §4 **Tier-A** recommended-next
follow-up. A **pure key-collision report** over change-request
intakes, composing with the shipped ECR intake contract.

R1 is **pure, REPORT ONLY**: a module + tests + this MD. No
enforcement, no `assert_*`, no raiser, no DB, no schema, no runtime.
`ecr_intake_contract` is reused **unchanged**.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/ecr_dedupe_contract.py`
- `src/yuantus/meta_engine/tests/test_ecr_dedupe_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_ECR_DEDUPE_CONTRACT_R1_20260516.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`ecr_intake_contract` (reused unchanged), all services/routers/models,
and the prior R2 contracts are **unchanged**.

## 3. Contract

- `ChangeRequestReferenceCollision` — frozen dataclass: `reference`,
  `keys` (caller keys of the ≥2 colliding intakes, input order).
- `ChangeRequestDedupeReport` — frozen dataclass: `total`,
  `unique_references`, `collisions` (only refs with ≥2 keys, **sorted
  by reference**, keys in input order), `has_collisions`
  (`len(collisions) > 0` — a neutral name; this is a report, **not** a
  gate; there is no `ok`).
- `build_change_request_dedupe_report(items)` — pure. `items` is
  `Sequence[tuple[caller_key, ChangeRequestIntake]]`. Reference is
  obtained via the **imported**
  `ecr_intake_contract.derive_change_request_reference` (reused, never
  reimplemented). Groups by reference; emits one collision per
  reference with ≥2 keys. Duplicate caller keys are allowed (caller
  owns key semantics — not validated). Deterministic output.

### Report-only boundary (owner-scoped, taskbook §3/§8)

No `assert_*`, no raiser, no enforcement, no merge/drop/reject, no DB,
no schema, no runtime. The module raises **nothing at all** — pinned by
an AST guard.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_ecr_dedupe_contract.py` (test
groups; counts are a point-in-time snapshot):

- Empty input → zeros, no collisions, `has_collisions=False`.
- All-distinct → no collisions; `unique_references == total`.
- Two intakes that differ only in `reason`/`priority` (NOT reference
  fields) → exactly one collision grouping their two keys in input
  order; the collision's `reference` equals the shipped derivation.
- 3-way collision + an unrelated unique → one collision with three
  keys; `unique_references` correct.
- Deterministic ordering: `collisions` sorted by `reference`; within a
  group `keys` in input order; the function is pure (same input →
  identical report).
- Duplicate caller keys are grouped, not validated/rejected.
- **Composition / drift guard**: the report's reference equals
  `ecr_intake_contract.derive_change_request_reference(intake)` — a
  change to the shipped reference is reflected, not shadowed.
- **No-enforcement guard** (AST): the module exposes no callable named
  `assert_*` and contains **no `raise`** at all (report-only).
- **Purity guard** (AST): imports nothing from `yuantus.database` /
  `sqlalchemy` / a router / `plugins` / any `*_service`; imports
  **only** `yuantus.meta_engine.services.ecr_intake_contract`.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ecr_dedupe_contract.py \
  src/yuantus/meta_engine/tests/test_ecr_intake_contract.py
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
  src/yuantus/meta_engine/services/ecr_dedupe_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

Observed as of 2026-05-16: dedupe contract tests passed; ECR-intake
regression passed (compose dependency, unchanged); doc-index trio +
portfolio drift guard passed; py_compile clean; `git diff --check`
clean.

## 6. Non-Goals (reaffirmed from taskbook §8)

No enforcement (`assert_*`/raiser/merge/drop/reject); no DB / schema /
migration / tenant-baseline; no edit to `ecr_intake_contract` or any
service/router; no feature flag; no `eval`; no data migration; no
runtime wiring. No contact with the other R2 contracts. `.claude/` and
`local-dev-env/` stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- **Dedupe enforcement** — an opt-in caller that rejects/merges on
  collision (touches DB/permissions).
- **Reference persistence** — storing references for cross-request
  dedupe over time (schema).
