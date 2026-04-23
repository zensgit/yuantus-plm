# File Router Decomposition R3 Storage - Development And Verification

Date: 2026-04-23

## 1. Goal

Split file storage routes out of legacy `file_router.py` into `file_storage_router.py` without changing the public `/api/v1/file/*` API.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/file_storage_router.py`.
- Registered `file_storage_router` after `file_viewer_router` and before legacy `file_router` in `src/yuantus/api/app.py`.
- Moved upload/download/preview DTOs, helpers, and route handlers into the split router.
- Added `test_file_storage_router_contracts.py`.
- Updated upload tests to patch the new storage-router owner module.
- Registered the new contract test and pact/provider surface trigger in `.github/workflows/ci.yml`.
- Kept metadata and item-file attachment routes in legacy `file_router.py`.

## 3. Public API

Unchanged:

- `POST /api/v1/file/upload`
- `GET /api/v1/file/{file_id}/download`
- `GET /api/v1/file/{file_id}/preview`

## 4. Contract Coverage

The new route ownership contract asserts:

- moved routes are owned by `file_storage_router`;
- `file_router.py` no longer declares moved route decorators;
- registration order is `file_conversion_router` -> `file_viewer_router` -> `file_storage_router` -> legacy `file_router`;
- moved routes are registered exactly once;
- File Management tag is preserved;
- metadata and attachment routes remain outside the storage router.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/file_storage_router.py \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/meta_engine/web/file_viewer_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

git diff --check
```

Results:

- py_compile: pass
- R3 storage focused tests: 10 passed
- adjacent file-router regression: 60 passed
- pact provider + doc-index + CI list contracts: 5 passed
- `git diff --check`: pass

## 6. Non-Goals

- No metadata route split.
- No attachment route split.
- No conversion or viewer route changes.
- No service-layer behavior changes.
- No schema, migration, settings, scheduler, shared-dev `142`, or UI changes.

## 7. Follow-Up

R4 should split the remaining metadata and attachment routes only after R3 is merged and post-merge validation is green. Attachment write paths have lock/version semantics, so they should remain a separate review slice.
