# P1 Version File-Level Checkout

Date: 2026-04-15

## Goal

Add the missing `VersionFile`-level checkout slice on clean mainline without
re-opening the larger CAD write surface:

1. add file-level lock fields to `meta_version_files`
2. expose service methods for file checkout / undo / lock lookup
3. add HTTP endpoints under `/api/v1/versions/{version_id}/files/{file_id}/...`
4. close the lock lifecycle so version `checkin()` and `release()` do not leave
   orphan file locks

## Scope

Touched files:

- `migrations/versions/d2e3f4a5b6c7_add_version_file_checkout_fields.py`
- `src/yuantus/meta_engine/version/models.py`
- `src/yuantus/meta_engine/version/file_service.py`
- `src/yuantus/meta_engine/version/service.py`
- `src/yuantus/meta_engine/web/version_router.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_service.py`
- `src/yuantus/meta_engine/tests/test_version_file_checkout_router.py`
- `src/yuantus/meta_engine/tests/test_version_service.py`

## What changed

### 1. `VersionFile` now carries file-level lock state

`VersionFile` gained:

- `checked_out_by_id`
- `checked_out_at`

The matching migration adds the same columns to `meta_version_files` and wires
`checked_out_by_id -> rbac_users.id`.

### 2. `VersionFileService` now supports file checkout lifecycle

New service methods:

- `checkout_file(...)`
- `undo_checkout_file(...)`
- `get_file_lock(...)`
- `get_blocking_file_locks(...)`
- `release_all_file_locks(version_id)`

Behavior:

- released versions reject file checkout
- a version checked out by another user rejects file checkout
- file ids attached with multiple roles require explicit `file_role`
- repeated checkout by the same user is idempotent

### 3. `VersionService` now respects file-level locks

`VersionService.checkout()` now refuses to take a whole-version checkout if the
target version already has file-level locks held by another user.

`VersionService.checkin()` now clears all file-level locks on that version after
syncing version files.

`VersionService.release()` now also clears file-level locks so release cannot
leave orphan file locks behind.

### 4. New HTTP endpoints

Added:

```text
POST /api/v1/versions/{version_id}/files/{file_id}/checkout
POST /api/v1/versions/{version_id}/files/{file_id}/undo-checkout
GET  /api/v1/versions/{version_id}/files/{file_id}/lock
```

Also enriched existing `GET /api/v1/versions/{version_id}/files` responses with:

- `checked_out_by_id`
- `checked_out_at`

### 5. Claude sidecar found one real lifecycle gap

I used a short read-only `Claude Code CLI` prompt after the first green focused
run. It pointed out one real edge case: `release()` cleared the version-level
checkout but did not clear file-level locks.

That gap was fixed in the same slice, and a `VersionService` regression was
added for it.

## Verification

### Focused file-checkout + version lifecycle regression

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py
```

Observed:

- `27 passed, 1 warning`

### Syntax check

```bash
PYTHONPATH=src python3 -m py_compile \
  src/yuantus/meta_engine/version/models.py \
  src/yuantus/meta_engine/version/file_service.py \
  src/yuantus/meta_engine/version/service.py \
  src/yuantus/meta_engine/web/version_router.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py
```

Observed:

- passed

### Warning note

The warning is the existing local `urllib3/LibreSSL` environment warning. It is
not introduced by this slice.

## Outcome

Clean mainline now has the missing file-level lock primitive:

`Version checkout -> VersionFile checkout -> file lock lookup -> undo checkout -> checkin/release clears locks`

This closes the gap between the already-merged CAD queue/read surface work and
the next step of enforcing file-level edit guards on more write paths.

## Claude Code CLI

This slice did call `Claude Code CLI`, but only for a short read-only sidecar
sanity check.

Observed behavior:

- authenticated and callable
- short prompt returned successfully
- useful for catching one lifecycle edge
- still not the right primary execution path for core write-path changes
