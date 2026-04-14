# P1 File Conversion Summary

Date: 2026-04-14

## Goal

Continue the canonical CAD read-surface work after `checkin-status` by adding a
file-level conversion summary:

1. give clients a stable file-centric polling endpoint
2. unify current `meta_conversion_jobs` and legacy `cad_conversion_jobs` behind
   one read surface
3. link the item-level CAD checkin responses to that file-level surface

## Scope

Touched files:

- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py`
- `src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py`

## What changed

### 1. Added canonical file-level summary

New endpoint:

```text
GET /api/v1/file/{file_id}/conversion_summary
```

It returns:

- `file_id`
- `filename`
- `conversion_status`
- `conversion_jobs[]`
- `conversion_jobs_summary`
- `viewer_readiness`

### 2. Read path now spans both queues

The new summary endpoint reads:

- current queue:
  - `meta_conversion_jobs`
- legacy queue:
  - `cad_conversion_jobs`

The response marks each job with:

- `source`: `meta` or `legacy`
- `task_type`
- `target_format`
- `operation_type`
- `status`
- `error_message`
- `result_file_id`

This keeps the write-path migration small while giving callers one place to
poll.

### 3. CAD checkin surfaces now point to file-level summary

These CAD responses now include `file_status_url`:

- `POST /api/v1/cad/{item_id}/checkin`
- `GET /api/v1/cad/{item_id}/checkin-status`

So the item-level path can hand off directly to the file-level path.

### 4. Viewer-readiness constructor alignment fixed

The new file summary endpoint already used:

- `CADConverterService(db, vault_base_path=VAULT_DIR)`

`cad_router` had been using `CADConverterService(db)` without an explicit vault
path. This was aligned so both routes now use the same local vault base path
source, avoiding inconsistent readiness results under non-default local storage
roots.

## Verification

### Focused router slice

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py
```

Observed:

- `24 passed, 1 warning`

### Related read-surface regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py
```

Observed:

- `40 passed, 1 warning`

### Targeted consistency rerun after vault-path alignment

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

Observed:

- `46 passed, 1 warning`

### Syntax check

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/cad_router.py
```

Observed:

- passed

### Warning note

The warning is the existing local `urllib3/LibreSSL` environment warning. It is
not introduced by this change.

## Outcome

The clean mainline CAD read surface now has two canonical layers:

- item-level:
  - `GET /api/v1/cad/{item_id}/checkin-status`
- file-level:
  - `GET /api/v1/file/{file_id}/conversion_summary`

This makes the current closed loop:

`checkin -> queue jobs -> worker binds derived roles -> item-level status -> file-level summary -> viewer readiness`

## Claude Code CLI

This round did call `Claude Code CLI` as a read-only sidecar.

Observed:

- authenticated and callable
- the short design prompt returned concrete guidance
- it correctly flagged a real consistency risk:
  `CADConverterService(db)` vs `CADConverterService(db, vault_base_path=...)`

That risk was fixed in the implementation. The CLI was useful for read-only
review, but core code changes and verification remained local.
