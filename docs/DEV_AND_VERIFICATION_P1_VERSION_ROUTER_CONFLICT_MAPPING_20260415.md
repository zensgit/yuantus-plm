# P1 Version Router Conflict Mapping

## Scope
- Align `checkout` and `checkin` router error mapping with the existing version/file lock contract.
- Treat foreign version checkout and foreign file-lock conflicts as HTTP `409` instead of generic `400`.

## Code Changes
- `src/yuantus/meta_engine/web/version_router.py`
  - `checkout()` now routes `VersionError` through `_raise_version_http_error(...)`.
  - `checkin()` now routes `VersionError` through `_raise_version_http_error(...)`.
  - `_raise_version_http_error(...)` now treats `file-level lock` / `locks held` messages as `409 Conflict`.
- `src/yuantus/meta_engine/tests/test_version_checkout_checkin_router.py`
  - Added HTTP-level regression tests for `checkout`/`checkin` conflict mapping.
- `docs/DELIVERY_DOC_INDEX.md`
  - Added this delivery document entry.

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_version_checkout_checkin_router.py src/yuantus/meta_engine/tests/test_version_source_checkout_router.py src/yuantus/meta_engine/tests/test_version_service.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
  - `21 passed, 1 warning`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/web/version_router.py src/yuantus/meta_engine/tests/test_version_checkout_checkin_router.py`
  - passed

## Result
- `checkout` and `checkin` now return `409` for lock-contract conflicts instead of collapsing them into `400`.
- Existing `404` and generic validation behavior remain unchanged.
- No full-repo regression was run for this slice.
