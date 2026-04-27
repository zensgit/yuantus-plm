# Claude Task — Phase 3 Tenant Import Rehearsal

Date: 2026-04-27

## 1. Goal

Prepare the bounded implementation plan for P3.4.2 tenant import rehearsal.

P3.4.2 is the first phase that may write tenant application rows into a
non-production PostgreSQL tenant schema. Because the required external inputs
are not available yet, this taskbook is intentionally design-only and must not
be implemented until the stop-gate inputs are provided.

## 2. Required External Inputs

Implementation must not start until all are true:

- A named pilot tenant is approved.
- A non-production PostgreSQL rehearsal DSN is available.
- A backup/restore owner is named.
- A rehearsal window is scheduled.
- `docs/TENANT_TABLE_CLASSIFICATION_20260427.md` is signed off.
- P3.4.1 dry-run report exists and has `ready_for_import=true`.

## 3. Scope For The Future Implementation PR

When authorized, implement a rehearsal-only importer that:

- reads a P3.4.1 dry-run JSON report;
- validates the report schema and `ready_for_import=true`;
- connects to the source DB read-only;
- connects to the non-production target PostgreSQL DB;
- asserts the target schema exists and is at `t1_initial_tenant_baseline`;
- imports only tables from `tenant_tables_in_import_order`;
- excludes every table in `GLOBAL_TABLE_NAMES`;
- writes a JSON and Markdown rehearsal result with row counts and blockers.

The importer must be explicit about rehearsal scope. It must not be usable for
production cutover by accident.

## 4. Non-Goals

- No production database access.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No cutover config changes.
- No source writes.
- No global/control-plane table import.
- No schema creation or migration; that remains the runbook's separate
  provision/upgrade step.
- No automatic rollback or destructive cleanup.

## 5. Required Future Interface

Proposed CLI:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --source-url <source-db-url> \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --output-json output/tenant_<tenant-id>_import_rehearsal.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal.md \
  --confirm-rehearsal
```

`--confirm-rehearsal` must be required. Without it, exit 2 before opening any
database connection.

The implementation should fail closed if:

- the dry-run report schema version is not `p3.4.1-dry-run-v1`;
- `ready_for_import` is false;
- the dry-run target schema differs from `--target-schema`;
- the target database is not PostgreSQL;
- the target schema is missing;
- `<schema>.alembic_version` is not `t1_initial_tenant_baseline`;
- any source table outside the dry-run import order is requested;
- any `GLOBAL_TABLE_NAMES` table appears in the import plan.

## 6. Rehearsal Result Shape

The future result should include:

- `schema_version`: `p3.4.2-import-rehearsal-v1`
- `tenant_id`
- `target_schema`
- redacted `source_url`
- redacted `target_url`
- `baseline_revision`
- `tables_imported`
- `source_row_counts`
- `target_row_counts`
- `row_count_mismatches`
- `skipped_global_tables`
- `started_at`
- `finished_at`
- `ready_for_cutover`: always false in P3.4.2
- `blockers`

`ready_for_cutover` must remain false because P3.4.2 is rehearsal only.

## 7. Test Requirements For The Future Implementation

Use SQLite fixtures for pure planning and import-shape tests. Use PostgreSQL
integration tests only when `YUANTUS_TEST_PG_DSN` is set.

Minimum tests:

- missing `--confirm-rehearsal` exits 2 before DB connection;
- dry-run report schema mismatch blocks;
- `ready_for_import=false` blocks;
- target schema mismatch blocks;
- target non-PostgreSQL URL blocks;
- missing target schema blocks;
- wrong `alembic_version` blocks;
- global/control-plane table import is impossible;
- row-count mismatch is reported;
- successful rehearsal imports representative tenant tables into a unique
  non-production schema and leaves `ready_for_cutover=false`;
- all URLs are redacted in JSON/Markdown reports.

## 8. Verification Commands For This Taskbook PR

This taskbook-only PR should run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

No runtime tests are required for this design-only PR.
