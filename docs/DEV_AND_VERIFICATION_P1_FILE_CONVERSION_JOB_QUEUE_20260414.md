# P1 File Conversion Job Queue

Date: 2026-04-14

## Goal

Continue the clean-mainline CAD convergence work by moving the file conversion
router endpoints onto the canonical async queue:

1. make `POST /api/v1/file/{file_id}/convert` write `meta_conversion_jobs`
2. make `GET /api/v1/file/conversion/{job_id}` read `meta -> legacy`
3. make `GET /api/v1/file/conversions/pending` read the canonical queue first
4. make `POST /api/v1/file/conversions/process` process only conversion jobs
5. shrink `POST /api/v1/file/process_cad` into a compat shim

## Scope

Touched files:

- `src/yuantus/meta_engine/services/job_service.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py`

Related read-surface regression coverage:

- `src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py`
- `src/yuantus/meta_engine/tests/test_checkin_manager.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py`
- `src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
- `src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py`

## What changed

### 1. `/file/{file_id}/convert` now writes the canonical queue

The route no longer calls `CADConverterService.create_conversion_job()` against
legacy `cad_conversion_jobs`.

It now:

- validates the source `FileContainer`
- classifies target formats into:
  - `cad_preview` for `png/jpg/jpeg`
  - `cad_geometry` for all other conversion targets
- submits jobs through `JobService.create_job(...)`
- returns the old `ConversionJobResponse` shape via a new
  `_meta_job_to_response(...)` mapper

The write-path is now aligned with the queue already used by CAD checkin.

### 2. Conversion status is now dual-read

`GET /api/v1/file/conversion/{job_id}` now:

- checks `meta_conversion_jobs` first
- falls back to legacy `cad_conversion_jobs`

This preserves existing links while letting new queue ids resolve on the same
canonical status route.

### 3. Pending conversions now favor the canonical queue

`GET /api/v1/file/conversions/pending` now:

- lists pending/processing jobs from `meta_conversion_jobs` first
- scopes to conversion task types only:
  - `cad_conversion`
  - `cad_preview`
  - `cad_geometry`
- fills any remaining `limit` with legacy pending jobs

This keeps compatibility for old jobs without making legacy the primary read
surface.

### 4. `/file/conversions/process` now processes only conversion tasks

The endpoint no longer calls `CADConverterService.process_batch()`.

Instead it:

- uses `JobService.requeue_stale_jobs()`
- claims only conversion task types through a small `poll_next_job(..., task_types=...)`
  extension
- builds a focused `JobWorker` with:
  - `cad_conversion`
  - `cad_preview`
  - `cad_geometry`
- executes jobs and reports:
  - `processed`
  - `succeeded`
  - `failed`

This avoids accidentally draining unrelated async jobs from the shared queue.

### 5. `/file/process_cad` is now a compat shim

The deprecated legacy endpoint no longer falls back to a local subprocess path.

It now:

- validates `file_id`
- requires an existing `FileContainer`
- rejects non-CAD files the same way canonical `/convert` does
- queues the same canonical meta job
- returns:
  - `job_id`
  - `status_url`
  - `viewable_url`
- adds:
  - `Deprecation: true`
  - `Sunset`
  - `Link: rel=\"successor-version\"`

## Verification

### Focused queue + router slice

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py
```

Observed:

- `22 passed, 9 warnings`

Warnings:

- existing local `urllib3/LibreSSL` environment warning
- Pydantic deprecation warnings inside this mock-heavy route test file

No test failed.

### Wider related regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py
```

Observed:

- `69 passed, 9 warnings`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/services/job_service.py
```

Observed:

- passed

## Outcome

The clean-mainline CAD conversion surface is now closer to a single canonical
queue model:

- write:
  - `POST /api/v1/file/{file_id}/convert`
- read status:
  - `GET /api/v1/file/conversion/{job_id}`
- read pending:
  - `GET /api/v1/file/conversions/pending`
- compat submit:
  - `POST /api/v1/file/process_cad`
- file-centric read summary:
  - `GET /api/v1/file/{file_id}/conversion_summary`

Legacy `cad_conversion_jobs` is still readable for compatibility, but it is no
longer the intended primary write path for these routes.

## Claude Code CLI

This round did invoke `Claude Code CLI` again as a read-only sidecar attempt.

Observed:

- CLI is logged in and callable in this clean worktree
- short probes are still fine
- this round's longer audit prompt did not return reliably inside the time
  window, so it was not used as a decision gate

Conclusion:

- `Claude` remains usable here as a sidecar
- core implementation and verification should still stay local unless the CLI
  session is clearly responsive
