# P1 CAD Checkin Status

Date: 2026-04-14

## Goal

Extend the clean-mainline CAD checkin queue slice with a canonical status
surface:

1. enhance `POST /api/v1/cad/{item_id}/checkin`
2. add `GET /api/v1/cad/{item_id}/checkin-status`
3. expose one stable place to read:
   - current version
   - native CAD file
   - conversion jobs
   - viewer readiness

## Scope

Touched files:

- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py`

The earlier queue-binding files remain part of the full slice:

- `src/yuantus/meta_engine/services/checkin_service.py`
- `src/yuantus/meta_engine/services/job_worker.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/cli.py`

## What changed

### 1. Checkin response is now actionable

`POST /api/v1/cad/{item_id}/checkin` now returns:

- `item_id`
- `version_id`
- `generation`
- `file_id`
- `conversion_job_ids`
- `status_url`

This removes the need for clients to guess where the just-created job ids were
stored.

### 2. Added canonical status endpoint

New endpoint:

```text
GET /api/v1/cad/{item_id}/checkin-status
```

It resolves:

- item
- current version
- native CAD file from `version.properties["native_file"]`
- anchored conversion jobs from `version.properties["cad_conversion_job_ids"]`
  when present
- fallback job discovery by `(item_id, version_id, file_id)` when anchor ids are
  absent
- viewer readiness via `CADConverterService.assess_viewer_readiness(...)`

### 3. Response contract

The endpoint returns:

- `item_id`
- `version_id`
- `file_id`
- `filename`
- `conversion_job_ids`
- `conversion_jobs[]`
- `conversion_jobs_summary`
- `viewer_readiness`

If any required link is missing, the endpoint returns `404`:

- item missing
- current version missing
- native file link missing
- native file record missing

## Verification

### Focused router + queue slice

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py
```

Observed:

- `21 passed, 1 warning`

### Wider related regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Observed:

- `40 passed, 1 warning`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/services/checkin_service.py \
  src/yuantus/meta_engine/services/job_worker.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py \
  src/yuantus/cli.py
```

Observed:

- passed

### Warning note

The warning is the existing local `urllib3/LibreSSL` environment warning. It is
not introduced by this change.

## Outcome

The clean mainline CAD path now has both:

- a canonical write path:
  - `POST /api/v1/cad/{item_id}/checkin`
- a canonical read/status path:
  - `GET /api/v1/cad/{item_id}/checkin-status`

So the current mainline CAD closed loop is now:

`checkin -> queue preview/geometry -> worker bind -> current item sync -> poll canonical checkin status`

## Claude Code CLI

This round did call `Claude Code CLI` for read-only sidecar inspection in the
clean worktree.

Observed behavior:

- authenticated and callable
- short read-only prompt returned successfully
- a later longer prompt returned enough guidance, but a previous prompt in the
  same session had already hit a time/usage window

Conclusion:

- `Claude` is usable here as a sidecar
- core implementation should still stay locally controlled unless the task is
  narrowly scoped and the CLI window is healthy
