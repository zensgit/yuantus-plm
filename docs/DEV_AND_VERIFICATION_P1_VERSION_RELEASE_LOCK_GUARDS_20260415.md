# P1 Version Release Lock Guards

Date: 2026-04-15

## Goal

Close the next version lifecycle bypass in the `VersionFile` lock model.

Before this slice, `VersionService.release(...)` would mark the current version
released and then clear all file-level locks on that version, even if some of
those locks were held by another user.

That made release a cross-user unlock path.

## Scope

Touched files:

- `src/yuantus/meta_engine/version/service.py`
- `src/yuantus/meta_engine/tests/test_version_service.py`

## What changed

### 1. `release()` now rejects foreign file locks

`VersionService.release(item_id, user_id)` now checks:

```python
self.file_version_service.get_blocking_file_locks(current_ver.id, user_id=user_id)
```

before it marks the version released.

If another user still holds file-level locks on the current version, release now
raises:

- `VersionError("Version has file-level locks held by another user (...)")`

### 2. Same-user release behavior remains unchanged

If no foreign file locks exist, `release()` still:

- marks the current version released
- clears the version-level checkout
- clears remaining file locks on that version via `release_all_file_locks(...)`

This preserves the prior “release closes your own lock lifecycle” behavior
without letting one user clear another user’s file locks.

## Verification

### Focused release regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Observed:

- `11 passed`

### Syntax check

```bash
PYTHONPATH=src python3 -m py_compile \
  src/yuantus/meta_engine/version/service.py \
  src/yuantus/meta_engine/tests/test_version_service.py
```

Observed:

- passed

## Claude Code CLI

This slice used `Claude Code CLI` as a short read-only sidecar to confirm the
policy decision:

- `release()` should reject foreign file locks rather than clear them

Core implementation and verification were executed locally.

## Outcome

The version/file lock model now covers:

- direct `VersionFile` mutation endpoints
- version-copy flows (`revise`, `new_generation`, `create_branch`)
- release-time lock ownership

This removes the last obvious lifecycle path where one user could clear another
user’s file locks by advancing the version state.
