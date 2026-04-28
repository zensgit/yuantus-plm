# Claude Task - Phase 3 Tenant Import Row Copy

Date: 2026-04-28

## 1. Goal

Implement the first guarded P3.4.2 tenant import rehearsal row-copy path behind
the existing `tenant_import_rehearsal` fail-closed scaffold.

## 2. Scope

- Keep the implementation packet and fresh artifact validation gates.
- Require `--confirm-rehearsal`.
- Require runtime `--source-url` and `--target-url`.
- Require target URL to be PostgreSQL.
- Require redacted runtime URLs to match the plan/packet URLs.
- Require managed target schema pattern `^yt_t_[a-z0-9_]+$`.
- Import only tables from `tenant_tables_in_import_order`.
- Fail closed if the plan includes global/control-plane tables.
- Fail closed if `source_row_counts` is missing any planned table.
- Copy rows in plan order with a configurable `--batch-size`.
- Write JSON and Markdown rehearsal reports with table-level row counts.
- Report `ready_for_rehearsal_import=true` only after all copied row counts
  match the plan.
- Keep `ready_for_cutover=false`.

## 3. Non-Goals

- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No schema creation, Alembic upgrade/downgrade, or schema cleanup.
- No automatic rollback or destructive cleanup.
- No global/control-plane table import.
- No automatic discovery/import of source tables outside the plan allowlist.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --source-url "$SOURCE_DATABASE_URL" \
  --target-url "$TARGET_DATABASE_URL" \
  --output-json output/tenant_<tenant-id>_import_rehearsal.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal.md \
  --confirm-rehearsal \
  --strict
```

## 5. Acceptance

The command returns 0 in `--strict` mode only when:

- all scaffold/packet/fresh-artifact guards pass;
- source and target runtime URLs are supplied and match redacted artifact URLs;
- target URL is PostgreSQL;
- target schema is managed;
- every planned table has a source row count;
- every copied table inserts exactly the expected number of rows.

## 6. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py

git diff --check
```
