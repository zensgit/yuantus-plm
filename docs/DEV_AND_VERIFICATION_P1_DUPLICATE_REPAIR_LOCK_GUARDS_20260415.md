# P1 Duplicate Repair Lock Guards

Date: 2026-04-15

## Summary

This slice closes the remaining duplicate-repair bypass on the canonical file ingest surface.

Before this change:

- `POST /api/v1/file/upload` could repair a missing storage object for an existing deduped `FileContainer`
- `POST /api/v1/cad/import` could do the same on checksum-hit imports

Neither path checked current-version `VersionFile` locks before rewriting the backing blob at `system_path`.

After this change, both endpoints reject duplicate-repair writes when the existing file is still part of a current version that is:

- released
- checked out by another user
- file-locked by another user on the current-version `file_id + file_role` slot

If there is no current-version `VersionFile` association, duplicate repair still proceeds.

## Code Changes

- `src/yuantus/meta_engine/web/file_router.py`
  - added `_ensure_duplicate_file_repair_editable(...)`
  - `POST /api/v1/file/upload` now accepts optional `user_id`
  - duplicate-repair branch now guards before `upload_file(...)`

- `src/yuantus/meta_engine/web/cad_router.py`
  - added `_ensure_duplicate_file_repair_editable(...)`
  - duplicate-repair branch in `POST /api/v1/cad/import` now guards before `upload_file(...)`

- `src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py`
  - added duplicate-repair conflict regression for `/file/upload`

- `src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py`
  - added duplicate-repair conflict regression for `/cad/import`

## Verification

Focused duplicate-repair suites:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py
```

Result: `8 passed, 1 warning`

Related lock-contract regression:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py
```

Result: `36 passed, 1 warning`

Compile check:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py
```

Result: passed

## Notes

- Warning remains the local `urllib3/LibreSSL` environment warning.
- No full-repo regression was run in this slice.
- `Claude Code CLI` was used only as a short read-only sidecar sanity check; implementation and verification were done locally.
