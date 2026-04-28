# DEV & Verification — Phase 3 Tenant Import Rehearsal Plan

Date: 2026-04-28

## 1. Goal

Create a DB-free import rehearsal plan manifest before the real P3.4.2 importer
is implemented.

This plan gives the future importer a deterministic input contract: exact table
order, source row-count expectations, and skipped global/control-plane tables.

## 2. Delivered

- `src/yuantus/scripts/tenant_import_rehearsal_plan.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_plan.py`
- `src/yuantus/scripts/tenant_import_rehearsal_next_action.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_next_action.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REHEARSAL_PLAN_20260428.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_PLAN_TODO_20260428.md`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The plan generator consumes:

- a P3.4.1 dry-run JSON report;
- a P3.4.2 Claude handoff JSON report.

It emits:

- JSON import plan;
- Markdown import plan;
- `ready_for_importer`;
- `ready_for_cutover=false`;
- blockers.

The plan is green only when the dry-run and handoff are green, tenant/schema
match, baseline revision is pinned, import order has no global/control-plane
tables, and row-count keys exactly match the import order.

## 4. Next-Action Integration

`tenant_import_rehearsal_next_action` now requires a green plan before setting
`claude_required=true`. This keeps the future importer implementation behind
four gates:

- dry-run;
- readiness;
- handoff;
- plan manifest.

## 5. Scope Controls

- No DB connection.
- No source or target mutation.
- No importer implementation.
- No schema create/drop/migration.
- No runtime setting change.
- No production cutover.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_plan.py \
  src/yuantus/scripts/tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py

git diff --check
```

## 7. Results

```text
plan/next-action/handoff/readiness/dry-run/doc-index: 48 passed, 1 warning in 0.77s
runbook/index contracts: 5 passed in 0.03s
py_compile: passed
git diff --check: clean
```

## 8. Next Step

Do not ask Claude to implement `tenant_import_rehearsal` until next-action says:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```
