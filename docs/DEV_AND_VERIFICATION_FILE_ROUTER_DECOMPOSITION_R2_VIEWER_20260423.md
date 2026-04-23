# File Router Decomposition R2 Viewer - Development And Verification

Date: 2026-04-23

## 1. Goal

Split viewer readiness, consumer summary, geometry asset, and CAD artifact read routes out of `file_router.py` into `file_viewer_router.py` without changing the public `/api/v1/file/*` API.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/file_viewer_router.py`.
- Registered `file_viewer_router` after `file_conversion_router` and before legacy `file_router` in `src/yuantus/api/app.py`.
- Moved viewer/C11 DTOs, helper functions, and 13 read route handlers into the split router.
- Added `test_file_viewer_router_contracts.py`.
- Registered the new contract test and pact/provider surface trigger in `.github/workflows/ci.yml`.
- Kept `file_router.py` focused on upload, metadata, download, preview, and item-file attachment routes.

## 3. Public API

Unchanged:

- `GET /api/v1/file/{file_id}/viewer_readiness`
- `GET /api/v1/file/{file_id}/geometry/assets`
- `GET /api/v1/file/{file_id}/consumer-summary`
- `POST /api/v1/file/viewer-readiness/export`
- `POST /api/v1/file/geometry-pack-summary`
- `GET /api/v1/file/{file_id}/geometry`
- `GET /api/v1/file/{file_id}/asset/{asset_name}`
- `GET /api/v1/file/{file_id}/cad_asset/{asset_name}`
- `GET /api/v1/file/{file_id}/cad_manifest`
- `GET /api/v1/file/{file_id}/cad_document`
- `GET /api/v1/file/{file_id}/cad_metadata`
- `GET /api/v1/file/{file_id}/cad_bom`
- `GET /api/v1/file/{file_id}/cad_dedup`

## 4. Contract Coverage

The new route ownership contract asserts:

- moved routes are owned by `file_viewer_router`;
- `file_router.py` no longer declares moved route decorators;
- `file_viewer_router` is registered between `file_conversion_router` and legacy `file_router`;
- moved routes are registered exactly once;
- File Management tag is preserved;
- metadata, download, preview, upload, and attachment routes remain outside the viewer router.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/meta_engine/web/file_viewer_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
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
- R2 viewer focused tests: 42 passed
- R1 adjacent file-router regression: 37 passed
- pact provider + doc-index + CI list contracts: 5 passed
- `git diff --check`: pass

## 6. Non-Goals

- No upload route split.
- No attachment route split.
- No metadata route split.
- No download or preview route split.
- No service-layer behavior changes.
- No schema, migration, settings, scheduler, shared-dev `142`, or UI changes.

## 7. Follow-Up

R3 should split upload/download/preview only after R2 is merged and post-merge validation is green. Attachment routes should remain a separate later slice because they carry write-path lock semantics.
