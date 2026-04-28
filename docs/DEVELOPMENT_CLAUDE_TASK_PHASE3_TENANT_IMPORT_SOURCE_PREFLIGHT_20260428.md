# Claude Task - Phase 3 Tenant Import Source Preflight

Date: 2026-04-28

## 1. Goal

Add a read-only P3.4.2 source preflight before any actual import rehearsal
implementation starts.

The preflight answers:

```text
Is the source schema compatible with the planned tenant import table and column
contract?
```

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_source_preflight`.
- Consume the P3.4.2 import rehearsal plan JSON.
- Require `--confirm-source-preflight` before opening any DB connection.
- Inspect only source table names and column names.
- Check every planned tenant table exists in the source DB.
- Check every target metadata column exists in the corresponding source table.
- Report source extra columns without blocking.
- Emit JSON and Markdown preflight reports.
- Update next-action so Claude is required only after source and target
  preflight are both green.

## 3. Non-Goals

- No importer implementation.
- No row export or import.
- No source row reads.
- No target database access.
- No schema creation, migration, downgrade, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_source_preflight \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --source-url <source-db-url> \
  --output-json output/tenant_<tenant-id>_source_preflight.json \
  --output-md output/tenant_<tenant-id>_source_preflight.md \
  --confirm-source-preflight \
  --strict
```

## 5. Acceptance

`ready_for_importer_source=true` only when:

- the plan schema is `p3.4.2-import-rehearsal-plan-v1`;
- the plan has `ready_for_importer=true`;
- the plan has no blockers;
- the source URL is present;
- every table in `tenant_tables_in_import_order` exists in the source DB;
- every target metadata column exists in the matching source table.

`ready_for_cutover` must remain false.

## 6. Next-Action Integration

`tenant_import_rehearsal_next_action` must require a green source preflight
report after the import plan and before the target preflight report.

Missing or blocked source preflight reports must produce:

- `run_source_preflight`
- `fix_source_preflight_report`
- `fix_source_preflight_blockers`

Only the final state remains:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_source_preflight.py \
  src/yuantus/scripts/tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py

git diff --check
```
