# Claude Task — Phase 3 Tenant Import Rehearsal Plan Manifest

Date: 2026-04-28

## 1. Goal

Add a DB-free import rehearsal plan manifest for P3.4.2.

The manifest converts a green P3.4.1 dry-run report and a green Claude handoff
report into a deterministic table-level plan for the future importer.

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_plan`.
- Consume a P3.4.1 dry-run JSON report.
- Consume a P3.4.2 Claude handoff JSON report.
- Emit JSON and Markdown import plan reports.
- Pin tenant import order, source row-count expectations, and skipped global
  tables.
- Keep `ready_for_cutover=false`.
- Update next-action so Claude is required only after the plan is green.

## 3. Non-Goals

- No importer implementation.
- No database connections.
- No source or target writes.
- No schema creation, migration, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_plan \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --handoff-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_plan.md \
  --strict
```

## 5. Acceptance

`ready_for_importer=true` only when:

- dry-run schema is `p3.4.1-dry-run-v1`;
- handoff schema is `p3.4.2-claude-import-rehearsal-handoff-v1`;
- dry-run `ready_for_import=true`;
- handoff `ready_for_claude=true`;
- both reports have empty blockers;
- tenant id and target schema match;
- dry-run baseline revision is `t1_initial_tenant_baseline`;
- import order is non-empty;
- import order contains no global/control-plane table;
- row-count keys exactly match import-order tables.

## 6. Verification

Run:

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

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py

git diff --check
```
