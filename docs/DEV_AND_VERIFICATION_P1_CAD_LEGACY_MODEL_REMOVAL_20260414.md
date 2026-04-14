# P1 CAD Legacy Model Removal

Date: 2026-04-14

## Goal

Remove the dead legacy ORM model for `cad_conversion_jobs` while keeping the
delete-window audit operational.

This slice separates:

- code removal of the old mapped class
- audit visibility of whether the physical table still exists

so the later DB drop can be handled as an explicit migration step.

## Scope

Touched files:

- `src/yuantus/meta_engine/models/file.py`
- `scripts/audit_legacy_cad_conversion_jobs.py`
- `src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py`
- `docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_CONVERSION_QUEUE_AUDIT_20260414.md`
- `docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_DELETE_WINDOW_READINESS_20260414.md`

## What changed

### 1. Removed legacy ORM model from `models/file.py`

Deleted the legacy `ConversionJob` mapped class from:

- `src/yuantus/meta_engine/models/file.py`

The canonical async job model remains only in:

- `src/yuantus/meta_engine/models/job.py`

### 2. Audit script now reflects the table by name

`scripts/audit_legacy_cad_conversion_jobs.py` no longer imports the legacy ORM
class.

Instead it now:

- checks table existence via `inspect(bind).has_table("cad_conversion_jobs")`
- reflects the table dynamically with SQLAlchemy `Table(..., autoload_with=...)`
- keeps row-level audit behavior unchanged when the table exists
- returns zero rows cleanly when the table is already gone

### 3. Audit tests no longer depend on the removed model

The audit test suite now creates a minimal `cad_conversion_jobs` table directly
inside the in-memory test database, instead of importing a removed ORM class.

## Verification

### Focused audit + queue tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py
```

Observed:

- `25 passed, 5 warnings`

### Wider CAD/read-surface regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- `49 passed, 5 warnings`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/models/file.py \
  scripts/audit_legacy_cad_conversion_jobs.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py
```

Observed:

- passed

### Real audit dry-run

```bash
PYTHONPATH=src python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --limit 20 \
  --detail-limit 5 \
  --out-dir /tmp/yuantus-cad-legacy-audit \
  --json-out /tmp/yuantus-cad-legacy-audit/report.json
```

Observed:

- `legacy_table_present = false`
- `job_count = 0`
- `code_reference_count = 23`
- `code_reference_counts_by_scope.production = 1`
- `blocking_production_reference_count = 0`
- `delete_window_ready = true`

The only remaining production reference is:

- `src/yuantus/meta_engine/services/cad_converter_service.py`
  - deprecated compat shim method definition

## Outcome

This slice removes the dead legacy ORM layer without coupling that removal to
the physical table drop.

After this change:

- runtime code no longer depends on a mapped `cad_conversion_jobs` class
- the audit still works when the legacy table exists
- the audit still works when the legacy table is already absent

The next step can be a clean schema-removal slice if you want to drop the
physical `cad_conversion_jobs` table and trim remaining docs/runbooks.

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is logged in and callable
- its guidance about removing code first and dropping the table later matched
  the implementation direction

Core implementation and verification still remained local.
