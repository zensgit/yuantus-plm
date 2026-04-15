# P1 CAD Import Lock Guards

Date: 2026-04-15

## Summary

This slice closes a remaining `cad/import` write-path bypass in the file lock contract.

Before this change, `POST /api/v1/cad/import` only checked whole-version checkout ownership before updating or creating `ItemFile` rows on the current version's item. It did not check current-version `VersionFile` locks for the specific file/role slot, so an import could overwrite an attachment role while another user still held a file-level lock.

Now `cad/import` uses the same current-version attachment guard pattern as `file_router`:

- reject foreign whole-version checkout with `409`
- reject foreign file-level locks for the specific `file_id` / `file_role` with `409`
- still allow creation when the current version simply has no corresponding `VersionFile` association yet

## Code Changes

- `src/yuantus/meta_engine/web/cad_router.py`
  - added `_ensure_current_version_attachment_editable(...)`
  - wired guard into `import_cad()` before:
    - updating an existing `ItemFile` role
    - creating a new `ItemFile` link

- `src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py`
  - new focused router contract coverage for:
    - existing-link role update blocked by foreign file lock
    - new-link attach blocked by foreign file lock
    - missing current-version `VersionFile` association allowed

## Verification

Focused suite:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py
```

Result: `3 passed, 1 warning`

Related regression:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py
```

Result: `31 passed, 1 warning`

Compile check:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py
```

Result: passed

## Notes

- Warning remains the local `urllib3/LibreSSL` environment warning.
- No full-repo regression was run in this slice.
- `Claude Code CLI` was used only as a short read-only sidecar sanity check; implementation and verification were done locally.
