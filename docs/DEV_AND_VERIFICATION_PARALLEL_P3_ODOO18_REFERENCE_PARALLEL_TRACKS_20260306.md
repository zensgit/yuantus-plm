# Parallel P3 Odoo18 Reference Tracks - Development and Verification (2026-03-06)

## 1. Scope

This batch completed two execution items and one reference-analysis item:

1. Execute release note and hardening suggestions.
2. Verify no regression with strict gate.
3. Deep-read Odoo18 reference modules and produce parallel development candidates.

## 2. Implemented Changes

### 2.1 FastAPI lifecycle hardening

- File: `src/yuantus/api/app.py`
- Change:
  - replace deprecated `@app.on_event("startup"/"shutdown")` with `lifespan` context manager.
  - extracted startup/shutdown routines into `_run_startup` and `_run_shutdown`.

### 2.2 Pydantic v2 config hardening

- File: `src/yuantus/meta_engine/schemas/aml.py`
- Change:
  - migrate class-based `Config` to `ConfigDict`.
  - replace mutable defaults (`{}`, `[]`) with `Field(default_factory=...)`.

### 2.3 Release notes update

- Added: `docs/RELEASE_NOTES_v0.1.3_update_20260306.md`
- Updated index entry in `docs/DELIVERY_DOC_INDEX.md`.

### 2.4 Odoo18 reference mapping design

- Added design: `docs/DESIGN_PARALLEL_P3_ODOO18_REFERENCE_PARALLEL_TRACKS_20260306.md`

## 3. Verification

### 3.1 Targeted regression

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py
```

Result: `125 passed`.

### 3.2 Documentation index contracts

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_*.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_*.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py
```

Result: `13 passed`.

### 3.3 Full strict gate

```bash
bash scripts/strict_gate.sh
```

Result: `STRICT_GATE: PASS`

- non-DB pytest: `235 passed`
- DB pytest: `599 passed`
- Playwright: `21 passed, 1 skipped`

## 4. Quality Delta

- Removed deprecated FastAPI lifecycle warnings caused by `on_event` hooks.
- Removed Pydantic class-config deprecation warnings for AML schemas.
- Remaining notable warning in full gate is unrelated legacy model deprecation in bootstrap path.

## 5. Parallel Track Candidates from Odoo18

See design file:

- `docs/DESIGN_PARALLEL_P3_ODOO18_REFERENCE_PARALLEL_TRACKS_20260306.md`

Immediate recommended P0 tracks:

1. Checkout gate strictness (`warn|block`) + threshold controls.
2. Breakage grouped counters by BOM/MBOM/Routing dimensions.
3. BOM compare mode strategy extension (`only_product` / `num_qty` / summarized).
