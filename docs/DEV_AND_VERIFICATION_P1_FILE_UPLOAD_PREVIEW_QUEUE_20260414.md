# P1 File Upload Preview Queue

Date: 2026-04-14

## Goal

Continue the clean-mainline CAD convergence work by removing the remaining
legacy preview queue write from `POST /api/v1/file/upload`.

This slice does three things:

1. move CAD upload auto-preview submission onto `meta_conversion_jobs`
2. return a stable file-level status surface in the upload response
3. keep non-CAD and duplicate-upload behavior unchanged

## Scope

Touched files:

- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py`

Related queue/read-surface regression coverage:

- `src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py`
- `src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py`
- `src/yuantus/meta_engine/tests/test_checkin_manager.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

## What changed

### 1. CAD upload preview submission now uses the canonical queue

Before this change, `POST /api/v1/file/upload` still used:

- `CADConverterService.create_conversion_job(...)`

which writes legacy `cad_conversion_jobs`.

Now the route reuses the same `_queue_file_conversion_job(...)` helper used by
the canonical file conversion routes, so CAD uploads submit:

- `cad_preview`

through `JobService.create_job(...)` into `meta_conversion_jobs`.

The upload path no longer reintroduces a second queue writer.

### 2. Upload response now includes a stable file status surface

`FileUploadResponse` now includes:

- `file_status_url`
- `conversion_job_ids`

For CAD uploads with auto-preview enabled:

- `conversion_job_ids` contains the queued preview job id
- `file_status_url` points to:
  - `GET /api/v1/file/{file_id}/conversion_summary`

For non-CAD uploads:

- `conversion_job_ids` is empty
- `file_status_url` is `null`

For duplicate CAD uploads:

- no new job is created
- the response still exposes `file_status_url`

### 3. Priority remains explicit for upload-generated preview work

The shared `_queue_file_conversion_job(...)` helper now accepts an optional
`priority`, and upload uses:

- `priority=50`

This preserves the intent of the old upload preview path while keeping the
write-path canonical.

## Verification

### Focused upload + queue slice

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py
```

Observed:

- `18 passed, 9 warnings`

Warnings:

- existing local `urllib3/LibreSSL` environment warning
- Pydantic deprecation warnings in the mock-heavy queue router test

### Wider related regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Observed:

- `65 passed, 9 warnings`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/web/file_router.py
```

Observed:

- passed

## Outcome

The clean-mainline CAD queue story is now more internally consistent:

- file upload preview submission
- file conversion submission
- conversion status lookup
- conversion summary

all point at the same canonical queue model first, with legacy reads retained
only where compat still matters.

## Claude Code CLI

This round again attempted to use `Claude Code CLI` as a read-only sidecar.

Observed:

- CLI remains authenticated and callable
- short probes work
- longer read-only prompts did not return reliably inside the short time window

So this slice was still implemented and verified locally, with `Claude` treated
as optional sidecar capacity rather than the primary executor.
