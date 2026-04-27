# Claude Task — Phase 3 Tenant Migration Dry-Run

Date: 2026-04-27

## 1. Goal

Implement P3.4.1 read-only source inspection for schema-per-tenant migration
planning.

The dry-run must let an operator inspect a source database before any target
PostgreSQL schema, import, or runtime cutover work begins.

## 2. Scope

- Add a pure report builder for source DB inspection.
- Add a CLI that writes JSON and Markdown reports.
- Add contract tests for classification drift, row counts, blockers, and CLI
  exit behavior.
- Update the tenant migration runbook.
- Add a development and verification record.

## 3. Non-Goals

- No target database writes.
- No source row export payloads.
- No import or replay.
- No production schema creation.
- No `TENANCY_MODE=schema-per-tenant` enablement.
- No runtime cutover.

## 4. Source Of Truth

- `GLOBAL_TABLE_NAMES`
- `build_tenant_metadata()`
- `docs/TENANT_TABLE_CLASSIFICATION_20260427.md`
- `migrations_tenant/versions/t1_initial_tenant_baseline.py`

Because `build_tenant_metadata()` retains attribution FKs to global tables,
the dry-run import-order metadata must strip cross-schema FKs before calling
`sorted_tables`, matching the P3.3.3 baseline generator.

## 5. Required Interface

Function API:

```python
build_dry_run_report(source_url: str, tenant_id: str) -> dict
```

CLI:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_migration_dry_run \
  --source-url <url> \
  --tenant-id <tenant-id> \
  --output-json <path> \
  --output-md <path>
```

Add `--strict` so blockers return exit code 1. Invalid arguments or connection
errors return exit code 2.

## 6. Required Report Fields

- `schema_version`
- `tenant_id`
- `target_schema`
- redacted `source_url`
- `baseline_revision`
- `global_tables`
- `tenant_tables_in_import_order`
- `source_tables`
- `missing_tenant_tables`
- `excluded_global_tables_present`
- `unknown_source_tables`
- `row_counts`
- `ready_for_import`
- `blockers`

`ready_for_import` is true only when no tenant table is missing and no unknown
source table is present. Global/control-plane source tables are excluded and
do not block by themselves. `alembic_version` is allowed metadata.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/tests/test_tenant_table_classification_contracts.py \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_tenant_baseline_revision.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python scripts/generate_tenant_baseline.py --check
PYTHONPATH=src .venv/bin/python -c "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"
git diff --check
```
