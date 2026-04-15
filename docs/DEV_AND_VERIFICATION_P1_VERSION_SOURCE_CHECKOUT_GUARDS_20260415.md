# P1 Version Source Checkout Guards

Date: 2026-04-15

## Scope
- Guard `revise`, `new_generation`, and `create_branch` against source versions checked out by another user.
- Align `revise/create_branch` route behavior with existing lock-conflict semantics by returning HTTP `409`.
- Remove the body-supplied `user_id` from `create_branch` in favor of the authenticated user dependency.

## Changes
- `src/yuantus/meta_engine/version/service.py`
  - Added shared source-version checkout guard.
  - `revise(...)`, `new_generation(...)`, and `create_branch(...)` now reject source versions checked out by another user.
- `src/yuantus/meta_engine/web/version_router.py`
  - `revise(...)` and `create_branch(...)` now map lock conflicts through `_raise_version_http_error(...)`.
  - `create_branch(...)` now uses `Depends(get_current_user_id)` instead of a body `user_id`.
- Tests
  - extended `src/yuantus/meta_engine/tests/test_version_service.py`
  - extended `src/yuantus/meta_engine/tests/test_version_advanced.py`
  - added `src/yuantus/meta_engine/tests/test_version_source_checkout_router.py`

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_version_service.py src/yuantus/meta_engine/tests/test_version_advanced.py src/yuantus/meta_engine/tests/test_version_source_checkout_router.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/version/service.py src/yuantus/meta_engine/web/version_router.py src/yuantus/meta_engine/tests/test_version_service.py src/yuantus/meta_engine/tests/test_version_advanced.py src/yuantus/meta_engine/tests/test_version_source_checkout_router.py`

## Observed Result
- `22 passed, 1 warning`
- `py_compile` passed
