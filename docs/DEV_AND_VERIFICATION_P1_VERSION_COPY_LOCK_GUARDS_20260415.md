# P1 Version Copy Lock Guards

Date: 2026-04-15

## Goal

Close the next high-value bypass after file-level checkout and direct mutation
guards landed on mainline.

Before this slice, `revise`, `new_generation`, and `create_branch` copied
`VersionFile` rows into a new version even when the source version still had
file-level locks held by another user. That allowed a locked source file to be
cloned into a fresh, unlocked target version.

## Scope

Touched files:

- `src/yuantus/meta_engine/version/file_service.py`
- `src/yuantus/meta_engine/version/service.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`
- `src/yuantus/meta_engine/tests/test_version_service.py`
- `src/yuantus/meta_engine/tests/test_version_advanced.py`

## What changed

### 1. Guard the shared copy path

`VersionFileService.copy_files_to_version(...)` now accepts optional `user_id`.

When `user_id` is provided, it checks `get_blocking_file_locks(source_version_id, user_id=...)`
before copying any rows.

If the source version has file-level locks held by another user, it now raises:

- `VersionFileError("Source version has file-level locks held by another user (...)")`

Same-user locks are still allowed, and copied `VersionFile` rows remain
unlocked on the target version.

### 2. Propagate the guard to all version-creation flows

The three direct callers now pass `user_id` into the shared copy path and map
`VersionFileError` back to `VersionError`:

- `VersionService.revise(...)`
- `VersionService.new_generation(...)`
- `VersionService.create_branch(...)`

This also closes the indirect ECO path, because `ECOService.action_new_revision()`
uses `create_branch(...)`.

## Verification

### Focused version/file-copy regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_advanced.py
```

Observed:

- `22 passed`

### Additional indirect caller regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Observed:

- `14 passed`

### Syntax check

```bash
PYTHONPATH=src python3 -m py_compile \
  src/yuantus/meta_engine/version/file_service.py \
  src/yuantus/meta_engine/version/service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_advanced.py
```

Observed:

- passed

## Claude Code CLI

This slice used `Claude Code CLI` as a short read-only sidecar.

Its useful conclusion matched the local inventory:

- the highest-value remaining bypass after direct mutation guards was the shared
  `copy_files_to_version(...)` path used by `revise`, `new_generation`, and
  `create_branch`

Core implementation and verification were still executed locally.

## Outcome

The file-lock model now covers both:

- direct `VersionFile` mutation endpoints
- indirect version creation flows that clone `VersionFile` rows

This removes the easiest way to fork a locked source file into a new, unlocked
revision or branch.
