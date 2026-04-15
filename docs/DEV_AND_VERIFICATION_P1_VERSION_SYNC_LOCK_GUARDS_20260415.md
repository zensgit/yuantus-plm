# P1 Version Sync Lock Guards

Date: 2026-04-15

## Goal

Close the next synchronous write-path bypass in the `VersionFile` lock model.

Before this slice, `VersionService.checkin()` enforced version ownership, but the
bulk helper it called — `VersionFileService.sync_item_files_to_version(...)` —
did not receive the acting `user_id`. That meant the helper itself had no
explicit precondition around:

- whether the version was checked out by the caller
- whether foreign file-level locks still existed on the target version

## Scope

Touched files:

- `src/yuantus/meta_engine/version/file_service.py`
- `src/yuantus/meta_engine/version/service.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`
- `src/yuantus/meta_engine/tests/test_version_service.py`

## What changed

### 1. `sync_item_files_to_version(...)` now accepts `user_id`

When `user_id` is provided, the helper now refuses to run unless:

- the target version exists
- the target version is not released
- the target version is checked out by that same user
- the target version has no file-level locks held by another user

If any of those checks fail, it now raises a `VersionFileError` before touching
existing `VersionFile` rows.

### 2. `checkin()` now passes the acting user through

`VersionService.checkin(...)` now calls:

```python
self.file_version_service.sync_item_files_to_version(..., user_id=user_id)
```

So the batch sync helper is no longer an unscoped internal write path; it now
inherits the caller’s lock context.

### 3. Focused regressions cover both layers

New regressions verify:

- `sync_item_files_to_version(...)` rejects calls when the version is not
  checked out by the caller
- `sync_item_files_to_version(...)` rejects foreign file locks
- `VersionService.checkin(...)` passes `user_id`
- `VersionService.checkin(...)` surfaces sync lock failures as `VersionError`

## Verification

### Focused sync/checkin regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Observed:

- `24 passed`

### Syntax check

```bash
PYTHONPATH=src python3 -m py_compile \
  src/yuantus/meta_engine/version/file_service.py \
  src/yuantus/meta_engine/version/service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_service.py
```

Observed:

- passed

## Claude Code CLI

This slice used `Claude Code CLI` as a short read-only sidecar.

Its useful conclusion was that the next defensible synchronous slice after
`release()` was the batch sync path used by `checkin()`, rather than jumping
straight to background `job_worker` mutation logic.

Core implementation and verification were executed locally.

## Outcome

The synchronous lock model now covers:

- direct `VersionFile` mutation endpoints
- version-copy flows
- release-time ownership
- the batch `checkin -> sync_item_files_to_version` write path

This removes the last obvious synchronous helper that could mutate `VersionFile`
rows without being explicitly scoped to the acting user.
