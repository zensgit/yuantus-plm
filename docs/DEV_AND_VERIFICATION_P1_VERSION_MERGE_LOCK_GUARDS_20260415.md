# P1 Version Merge Lock Guards

Date: 2026-04-15

## Scope
- Guard `VersionService.merge_branch(...)` so it no longer bypasses the file-lock contract.
- Move the merge endpoint off body-supplied `user_id` and onto the authenticated user dependency.
- Map merge lock conflicts to HTTP `409` instead of generic `400`.

## Changes
- `src/yuantus/meta_engine/version/service.py`
  - Added foreign file-lock precondition helper.
  - `merge_branch(...)` now rejects:
    - source version checked out by another user
    - source version foreign file locks
    - released target versions
    - target versions not checked out by the acting user
    - target version foreign file locks
- `src/yuantus/meta_engine/web/version_router.py`
  - `POST /api/v1/versions/items/{item_id}/merge` now uses `Depends(get_current_user_id)`.
  - Added explicit `VersionError -> HTTPException` mapping so lock conflicts return `409`.
- Tests
  - Extended `src/yuantus/meta_engine/tests/test_version_merge.py`
  - Added `src/yuantus/meta_engine/tests/test_version_merge_router.py`

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_version_merge.py src/yuantus/meta_engine/tests/test_version_merge_router.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/version/service.py src/yuantus/meta_engine/web/version_router.py src/yuantus/meta_engine/tests/test_version_merge.py src/yuantus/meta_engine/tests/test_version_merge_router.py`

## Observed Result
- `9 passed, 1 warning`
- `py_compile` passed
