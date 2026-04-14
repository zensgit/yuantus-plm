# P1 CAD Legacy Table Drop Migration

Date: 2026-04-14

## Goal

Remove the physical `cad_conversion_jobs` table from the Alembic migration
chain now that:

- runtime code no longer depends on the legacy ORM model
- runtime read/write paths no longer depend on the legacy queue
- audit reports `delete_window_ready = true`

## Scope

Touched files:

- `migrations/versions/a2b2c3d4e7a6_drop_legacy_cad_conversion_jobs.py`
- `docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_TABLE_DROP_MIGRATION_20260414.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/RUNBOOK_CAD_LEGACY_CONVERSION_QUEUE_AUDIT.md`

## What changed

### 1. Added idempotent drop-table migration

New migration:

```text
migrations/versions/a2b2c3d4e7a6_drop_legacy_cad_conversion_jobs.py
```

Behavior:

- `upgrade()`
  - inspects the current schema
  - drops `ix_cad_conversion_jobs_status` if present
  - drops `cad_conversion_jobs` if present
  - no-ops cleanly if the table is already absent
- `downgrade()`
  - recreates `cad_conversion_jobs` with the original legacy columns and FKs
  - recreates `ix_cad_conversion_jobs_status` if missing

### 2. Kept audit compatibility

The audit script already reflects the table by name, so it continues to work
both before and after this migration is applied.

### 3. Updated runbook assumptions

The legacy audit runbook now treats:

- `legacy_table_present = false`

as a valid post-removal steady state instead of an exceptional condition.

## Verification

### Focused regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- `10 passed in 0.22s`

### Migration smoke on temp sqlite DB

```bash
rm -f /tmp/yuantus-legacy-drop-migration.db
YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus-legacy-drop-migration.db \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m alembic -c alembic.ini upgrade a2b2c3d4e7a6
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('/tmp/yuantus-legacy-drop-migration.db')
tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
versions = sorted(row[0] for row in conn.execute("select version_num from alembic_version"))
print("after_upgrade_has_cad_conversion_jobs=", 'cad_conversion_jobs' in tables)
print("after_upgrade_versions=", versions)
PY
YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus-legacy-drop-migration.db \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m alembic -c alembic.ini downgrade z1b2c3d4e7a5
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('/tmp/yuantus-legacy-drop-migration.db')
tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
versions = sorted(row[0] for row in conn.execute("select version_num from alembic_version"))
print("after_downgrade_has_cad_conversion_jobs=", 'cad_conversion_jobs' in tables)
print("after_downgrade_versions=", versions)
PY
```

Observed:

- repository currently has multiple Alembic heads, so `upgrade head` is ambiguous
- after `upgrade a2b2c3d4e7a6`: `after_upgrade_has_cad_conversion_jobs = False`
- after `upgrade a2b2c3d4e7a6`: `after_upgrade_versions = ['a2b2c3d4e7a6']`
- after `downgrade z1b2c3d4e7a5`: `after_downgrade_has_cad_conversion_jobs = True`
- after `downgrade z1b2c3d4e7a5`: `after_downgrade_versions = ['z1b2c3d4e7a5']`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  migrations/versions/a2b2c3d4e7a6_drop_legacy_cad_conversion_jobs.py
```

Observed:

- passed

### Post-removal audit smoke

```bash
YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus-legacy-drop-migration.db \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m alembic -c alembic.ini upgrade a2b2c3d4e7a6
PYTHONPATH=src python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --out-dir /tmp/yuantus-legacy-drop-audit \
  --json-out /tmp/yuantus-legacy-drop-audit/report.json
```

Observed:

- `legacy_table_present = false`
- `job_count = 0`
- `blocking_production_reference_count = 0`
- `delete_window_ready = true`

## Outcome

This slice finishes the schema side of legacy CAD queue removal.

After applying the migration:

- runtime code is already cut over
- the physical legacy table is removed from migrated databases
- audit still works and reports the post-removal state correctly

## Limits

- This round did not run full-repository regression
- Verification focused on the migration itself plus the two affected CAD queue/audit suites

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is logged in
- short prompt guidance remained usable

Core implementation and verification still remained local.
