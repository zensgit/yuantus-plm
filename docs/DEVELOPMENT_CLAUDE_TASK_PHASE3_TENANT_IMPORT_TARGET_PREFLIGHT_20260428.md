# Claude Task - Phase 3 Tenant Import Target Preflight

Date: 2026-04-28

## 1. Goal

Add a read-only P3.4.2 target preflight before any actual import rehearsal
implementation starts.

The preflight answers:

```text
Is the non-production PostgreSQL target schema ready for the future importer?
```

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_target_preflight`.
- Consume the P3.4.2 import rehearsal plan JSON.
- Require `--confirm-target-preflight` before opening any DB connection.
- Connect only to the operator-supplied PostgreSQL target URL.
- Check target schema existence.
- Check `<schema>.alembic_version` equals `t1_initial_tenant_baseline`.
- Check every planned tenant table exists in the target schema.
- Check no global/control-plane table exists in the target schema.
- Emit JSON and Markdown preflight reports.
- Update next-action so Claude is required only after target preflight is green.

## 3. Non-Goals

- No importer implementation.
- No row export or import.
- No source database access.
- No schema creation, migration, downgrade, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_target_preflight \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --output-json output/tenant_<tenant-id>_target_preflight.json \
  --output-md output/tenant_<tenant-id>_target_preflight.md \
  --confirm-target-preflight \
  --strict
```

## 5. Acceptance

`ready_for_importer_target=true` only when:

- the plan schema is `p3.4.2-import-rehearsal-plan-v1`;
- the plan has `ready_for_importer=true`;
- the plan has no blockers;
- the target URL is PostgreSQL;
- `--target-schema` matches the plan target schema;
- the target schema exists;
- `<schema>.alembic_version` is `t1_initial_tenant_baseline`;
- every table in `tenant_tables_in_import_order` exists in the target schema;
- no table in `GLOBAL_TABLE_NAMES` exists in the target schema.

`ready_for_cutover` must remain false.

## 6. Next-Action Integration

`tenant_import_rehearsal_next_action` must require a green target preflight
report after the import plan. Missing or blocked preflight reports must produce:

- `run_target_preflight`
- `fix_target_preflight_report`
- `fix_target_preflight_blockers`

Only the final state remains:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
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
  src/yuantus/scripts/tenant_import_rehearsal_target_preflight.py \
  src/yuantus/scripts/tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py

git diff --check
```
