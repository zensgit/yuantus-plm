# P1 CAD Legacy Queue Final Closeout

Date: 2026-04-14

## Goal

Record the final steady state after the legacy CAD conversion queue removal
program is complete enough that:

- runtime write/read paths no longer depend on `cad_conversion_jobs`
- the physical table has a drop migration
- post-removal audit passes with zero production references

This document supersedes earlier transitional assumptions from:

- `docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_DELETE_WINDOW_READINESS_20260414.md`
- `docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_MODEL_REMOVAL_20260414.md`
- `docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_TABLE_DROP_MIGRATION_20260414.md`

Those slice docs remain useful as historical trail, but this file is the
current steady-state closeout.

## What changed in this closeout slice

### 1. Removed the last dead runtime compat shim

Deleted `CADConverterService.create_conversion_job()` from:

- `src/yuantus/meta_engine/services/cad_converter_service.py`

Reason:

- the method had zero in-repo production callers
- the remaining references were its own compat tests
- canonical queue entrypoints already exist in `file_router`, `cad_router`,
  `checkin_service`, and `JobService`

### 2. Trimmed queue-shim tests to the still-live helper surface

Updated:

- `src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py`

The test file now covers the remaining canonical helper behavior:

- `get_pending_jobs()`
- `process_batch()`

It no longer preserves tests for a removed deprecated method.

### 3. Re-ran the legacy audit after shim removal

The audit now reports:

- `legacy_table_present = false`
- `job_count = 0`
- `code_reference_count = 18`
- `code_reference_counts_by_scope.production = 0`
- `blocking_production_reference_count = 0`
- `delete_window_ready = true`

Remaining references are now only in:

- scripts
- tests

## Verification

### Focused cleanup regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py
```

Observed:

- `18 passed, 5 warnings`

### Post-cleanup audit

```bash
PYTHONPATH=src python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --limit 20 \
  --detail-limit 5 \
  --out-dir /tmp/yuantus-cad-legacy-audit-final \
  --json-out /tmp/yuantus-cad-legacy-audit-final/report.json
```

Observed:

- `legacy_table_present = false`
- `job_count = 0`
- `code_reference_count = 18`
- `code_reference_counts_by_scope.production = 0`
- `blocking_production_reference_count = 0`
- `delete_window_ready = true`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/cad_converter_service.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  scripts/audit_legacy_cad_conversion_jobs.py
```

Observed:

- passed

## Current steady state

At this point:

- new CAD conversion work is canonical `meta_conversion_jobs` only
- legacy queue runtime reads are gone
- legacy ORM model is gone
- legacy physical table has an idempotent drop/recreate migration
- post-removal audit accepts `legacy_table_present = false`
- no production runtime references remain in audit output

## Recommended commit sequence

If this clean mainline worktree is turned into commits, the cleanest grouping is:

1. `baseline-switch-docs`
   - baseline switch runbooks / execution docs
2. `p1-cad-checkin-and-status`
   - queue binding, checkin status, file conversion summary
3. `p1-cad-file-router-queue-convergence`
   - file conversion job queue, upload preview queue
4. `p1-cad-legacy-audit-and-removal`
   - audit script
   - delete-window readiness
   - model removal
   - table-drop migration
   - final closeout

## Limits

- This closeout did not run full-repository regression
- It only re-ran the focused CAD queue/audit suites needed to prove the final
  cleanup state

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is logged in
- short prompts are usable for consistency checks

Core cleanup and verification still remained local.
