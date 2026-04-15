# P1 Version File Lock Guards

Date: 2026-04-15

## Goal

Close the smallest remaining gap after `VersionFile` checkout landed on mainline:
the direct version-file mutation endpoints still enforced version checkout, but
they did not reject edits when the specific `VersionFile` row was locked by
another user.

This slice adds per-file lock enforcement to the three direct write paths:

1. attach/update existing version-file associations
2. detach version-file associations
3. switch the primary file on a version

## Scope

Touched files:

- `src/yuantus/meta_engine/version/file_service.py`
- `src/yuantus/meta_engine/web/version_router.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_router.py`

## What changed

### 1. `VersionFileService` gained a reusable per-file edit guard

Added `ensure_file_editable(version_id, file_id, user_id, *, file_role=None)`.

It now rejects:

- released versions
- whole-version checkouts held by another user
- file-level locks held by another user
- ambiguous `file_id` lookups when the same file is attached with multiple roles

### 2. Attach/detach/set-primary now enforce file-level locks

`attach_file(...)`

- when updating an existing `(version_id, file_id, file_role)` association,
  now checks the specific row lock before mutating it
- when `is_primary=True`, now also rejects replacing a current primary that is
  file-locked by another user

`detach_file(...)`

- now accepts `user_id` and rejects detaching a file association that is locked
  by another user

`set_primary_file(...)`

- now accepts `user_id` and optional `file_role`
- rejects both:
  - selecting a target file locked by another user
  - clearing an existing primary that is locked by another user

### 3. Router endpoints now map lock conflicts to HTTP 409

The following endpoints now pass `user_id` into `VersionFileService` and reuse
`_raise_version_file_http_error(...)` so lock conflicts return `409` instead of
generic `400`:

- `POST /api/v1/versions/{version_id}/files`
- `DELETE /api/v1/versions/{version_id}/files/{file_id}`
- `PUT /api/v1/versions/{version_id}/files/primary`

`PUT /files/primary` now also accepts optional `file_role`, so callers can
disambiguate cases where the same `file_id` is bound multiple times with
different roles.

## Verification

### Focused service/router regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Observed:

- `36 passed, 1 warning`

### Syntax check

```bash
PYTHONPATH=src python3 -m py_compile \
  src/yuantus/meta_engine/version/file_service.py \
  src/yuantus/meta_engine/web/version_router.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py
```

Observed:

- passed

## Claude Code CLI

This slice did call `Claude Code CLI` as a short read-only sidecar.

Observed guidance:

- the right minimal enforcement surface is still `attach`, `detach`, and
  `set_primary`
- it is useful for quick slice sanity checks
- core implementation and verification remained local

## Outcome

Mainline file-level checkout no longer stops at the dedicated checkout/undo/lock
endpoints; it now also guards the direct version-file mutation APIs that would
otherwise bypass the lock model.
