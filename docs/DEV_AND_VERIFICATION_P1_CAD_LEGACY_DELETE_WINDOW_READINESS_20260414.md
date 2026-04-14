# P1 CAD Legacy Delete Window Readiness

Date: 2026-04-14

## Goal

Clear the last blocking runtime dependencies on legacy `cad_conversion_jobs`
before opening the delete window.

This slice removes legacy dual-read from `file_router`, converts
`CADConverterService` pending/process helpers into canonical worker shims, and
re-runs the legacy audit to prove the runtime cutover is ready.

## Scope

Touched files:

- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/services/cad_converter_service.py`
- `scripts/audit_legacy_cad_conversion_jobs.py`
- `src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py`
- `src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py`
- `src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py`
- `src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py`

## What changed

### 1. `file_router` is now meta-only for conversion reads

Removed legacy queue fallback from:

- `GET /api/v1/file/{file_id}/conversion_summary`
- `GET /api/v1/file/conversion/{job_id}`
- `GET /api/v1/file/conversions/pending`

These endpoints now read only `meta_conversion_jobs`.

`POST /api/v1/file/process_cad` remains as a deprecated compat shim, but it no
longer depends on the legacy ORM model or old queue reads.

### 2. `CADConverterService` no longer processes legacy rows

`CADConverterService.create_conversion_job()` was already a canonical queue shim.
This slice also moved:

- `get_pending_jobs()`
- `process_job()`
- `process_batch()`
- `process_conversion_queue()`

onto `JobService + JobWorker + canonical CAD task handlers`.

That removes the last runtime query path to legacy `cad_conversion_jobs` from
the service layer.

### 3. Audit blocking logic now treats the model definition as non-blocking

`src/yuantus/meta_engine/models/file.py` still contains the legacy table
definition. That row is now treated as non-blocking in the audit because it is
schema residue, not an active runtime dependency.

## Verification

### Focused fallback-removal regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
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
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/services/cad_converter_service.py \
  scripts/audit_legacy_cad_conversion_jobs.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
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

Remaining production references are expected non-blockers:

- `src/yuantus/meta_engine/services/cad_converter_service.py`
  - deprecated shim method definition

## Outcome

This slice completes the delete-window preparation for legacy CAD conversion
queue runtime dependencies.

At this point:

- no legacy queue rows exist in the current local database
- no blocking production runtime references remain
- the audit says the delete window is ready

The next step can move from “prepare” to “actual removal”, starting with the
legacy model and any now-dead tests or docs.

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is logged in
- short prompts work
- it agreed the delete window is not ready while blocking refs exist, which
  matched the pre-fix local audit

Core implementation and verification still remained local.
