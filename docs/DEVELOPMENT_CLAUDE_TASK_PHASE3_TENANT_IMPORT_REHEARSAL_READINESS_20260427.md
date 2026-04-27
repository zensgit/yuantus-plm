# Claude Task — Phase 3 Tenant Import Rehearsal Readiness

Date: 2026-04-27

## 1. Goal

Implement a safe readiness validator for P3.4.2 tenant import rehearsal.

This is a pre-import gate. It validates operator-provided stop-gate inputs and
the P3.4.1 dry-run report before any importer implementation is allowed to run.

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_readiness`.
- Accept operator stop-gate inputs as CLI arguments and one P3.4.1 dry-run JSON file.
- Emit JSON and Markdown readiness reports.
- Redact the non-production PostgreSQL DSN.
- Return non-zero in `--strict` mode when blockers exist.
- Add tests and update the tenant migration runbook.

## 3. Non-Goals

- No database connections.
- No source writes.
- No target writes.
- No import or replay.
- No production database access.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No schema creation, migration, rollback, or cleanup.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_readiness \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --tenant-id <tenant-id> \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --backup-restore-owner <name> \
  --rehearsal-window <iso-or-text-window> \
  --classification-artifact docs/TENANT_TABLE_CLASSIFICATION_20260427.md \
  --classification-signed-off \
  --output-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_readiness.md \
  --strict
```

## 5. Acceptance

Readiness is true only when:

- every external stop-gate argument is present;
- `--classification-signed-off` is supplied;
- classification artifact exists;
- target URL is PostgreSQL-shaped;
- dry-run schema version is `p3.4.1-dry-run-v1`;
- dry-run `ready_for_import=true`;
- dry-run blockers are empty;
- dry-run baseline revision is `t1_initial_tenant_baseline`;
- tenant id and target schema match the dry-run report.

## 6. Report Shape

The report schema version is `p3.4.2-import-rehearsal-readiness-v1` and includes:

- `tenant_id`
- `target_schema`
- redacted `target_url`
- `dry_run_schema_version`
- `ready_for_import`
- `ready_for_rehearsal`
- `checks`
- `blockers`

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py

git diff --check
```
