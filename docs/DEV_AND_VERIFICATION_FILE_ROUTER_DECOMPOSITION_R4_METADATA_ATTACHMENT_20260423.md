# File Router Decomposition R4 Metadata Attachment - Development And Verification

Date: 2026-04-23

## 1. Goal

Finish file-router decomposition by moving the remaining metadata and item-file association routes out of legacy `file_router.py` without changing the public `/api/v1/file/*` API.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/file_metadata_router.py`.
- Added `src/yuantus/meta_engine/web/file_attachment_router.py`.
- Registered both routers after `file_storage_router` and before the legacy `file_router` shell in `src/yuantus/api/app.py`.
- Reduced `src/yuantus/meta_engine/web/file_router.py` to an empty compatibility router import shell.
- Moved metadata DTO/helper and `GET /file/{file_id}` into `file_metadata_router.py`.
- Moved attachment DTO/helper and attach/list/detach handlers into `file_attachment_router.py`.
- Updated attachment lock-guard tests to patch the new attachment-router owner module.
- Added route ownership contracts for metadata and attachment routers.
- Registered the new contract tests and pact/provider surface triggers in `.github/workflows/ci.yml`.

## 3. Public API

Unchanged:

- `GET /api/v1/file/{file_id}`
- `POST /api/v1/file/attach`
- `GET /api/v1/file/item/{item_id}`
- `DELETE /api/v1/file/attachment/{attachment_id}`

## 4. Contract Coverage

The new route ownership contracts assert:

- moved routes are owned by their split routers;
- legacy `file_router.py` no longer declares runtime route decorators;
- registration order is `file_conversion_router` -> `file_viewer_router` -> `file_storage_router` -> `file_attachment_router` -> `file_metadata_router` -> legacy `file_router`;
- moved routes are registered exactly once;
- File Management tag is preserved;
- metadata, storage, and attachment route groups do not bleed into each other.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/file_attachment_router.py \
  src/yuantus/meta_engine/web/file_metadata_router.py \
  src/yuantus/meta_engine/web/file_storage_router.py \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/meta_engine/web/file_viewer_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_file_attachment_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_metadata_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_attachment_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_metadata_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
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
- R4 metadata/attachment focused tests: 52 passed
- adjacent file-router regression: 30 passed
- pact provider + doc-index + CI list contracts: 5 passed
- `git diff --check`: pass

## 6. Non-Goals

- No URL changes.
- No response schema changes.
- No service-layer behavior changes.
- No lock/version guard semantic changes.
- No schema, migration, settings, scheduler, shared-dev `142`, or UI changes.

## 7. Follow-Up

File router decomposition is complete after R4. The legacy `file_router.py` shell can be removed only after downstream imports stop depending on `yuantus.meta_engine.web.file_router.file_router`.
