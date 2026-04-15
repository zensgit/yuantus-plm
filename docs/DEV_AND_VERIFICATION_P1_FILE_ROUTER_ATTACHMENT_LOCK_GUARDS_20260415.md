# P1 File Router Attachment Lock Guards

## Scope
- Guard item attachment write endpoints against current-version `VersionFile` locks held by another user.
- Keep behavior permissive when the current version has no matching `VersionFile` association for the item attachment.

## Code Changes
- `src/yuantus/meta_engine/web/file_router.py`
  - Added `_ensure_current_version_attachment_editable(...)`.
  - `POST /api/v1/file/attach` now checks matching current-version `VersionFile` locks before:
    - updating an existing `ItemFile` role/description
    - creating a new `ItemFile` projection
  - `DELETE /api/v1/file/attachment/{attachment_id}` now checks matching current-version `VersionFile` locks before deleting the `ItemFile`.
- `src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py`
  - Added focused HTTP contract tests for locked current-version associations and the “missing version association is allowed” boundary.
- `docs/DELIVERY_DOC_INDEX.md`
  - Added this delivery document entry.

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
  - `6 passed, 1 warning`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/web/file_router.py src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py`
  - passed

## Result
- Item attachment writes no longer bypass current-version file locks when a matching `VersionFile` association is already protected by another user.
- New item attachments still work when the current version has no corresponding `VersionFile` row yet.
- No full-repo regression was run for this slice.
