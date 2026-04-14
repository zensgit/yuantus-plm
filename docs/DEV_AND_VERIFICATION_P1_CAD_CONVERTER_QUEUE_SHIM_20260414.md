# P1 CAD Converter Queue Shim

Date: 2026-04-14

## Goal

Stop `CADConverterService.create_conversion_job()` from creating new legacy
`cad_conversion_jobs` rows and redirect it to the canonical meta job queue.

## Scope

Touched files:

- `src/yuantus/meta_engine/services/cad_converter_service.py`
- `scripts/audit_legacy_cad_conversion_jobs.py`
- `src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py`
- `src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py`

## What changed

### 1. `create_conversion_job()` is now a queue shim

`CADConverterService.create_conversion_job()` no longer constructs legacy queue
rows directly.

It now:

- loads the source `FileContainer`
- maps preview-style requests to `cad_preview`
- maps convert-style requests to `cad_geometry`
- builds canonical payload fields such as `file_id`, `filename`,
  `cad_format`, and request-scope identity
- delegates to `JobService.create_job(...)`
- returns the created meta queue job id

Unsupported operations such as `printout` still fail fast.

### 2. Audit false positives were reduced

The legacy audit script previously over-counted production references whenever a
file imported `FileContainer` from `models.file` and `ConversionJob` from
`models.job`.

The scan now parses imports and only treats `query/get(ConversionJob)` as
legacy references when `ConversionJob` is actually bound from
`yuantus.meta_engine.models.file`.

That moved the dry-run summary from noisy counts to a real blocker set.

## Verification

### Focused shim + audit tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- `7 passed`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/services/cad_converter_service.py \
  scripts/audit_legacy_cad_conversion_jobs.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- passed

### Dry-run evidence pack

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
- `code_reference_count = 37`
- `code_reference_counts_by_scope.production = 8`
- `blocking_production_reference_count = 7`
- `delete_window_ready = false`

Remaining production blockers are now a narrow set:

- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/services/cad_converter_service.py`
- `src/yuantus/meta_engine/models/file.py`

## Outcome

This slice closes the last known legacy queue write shim outside `file_router`
and makes the delete-window audit useful again.

It does not remove dual-read compatibility yet. The next safe step is to clear
the remaining seven blocking production references, then rerun the audit.

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI is logged in and short probes work
- longer prompts remain less stable than local execution

Core implementation, testing, and dry-run verification were still completed
locally.
