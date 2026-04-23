# File Router Decomposition R1 Conversion - Development And Verification

Date: 2026-04-23

## 1. Goal

Split file conversion routes out of `file_router.py` into a dedicated `file_conversion_router.py` without changing the public `/api/v1/file/*` API.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/file_conversion_router.py`.
- Registered `file_conversion_router` before legacy `file_router` in `src/yuantus/api/app.py`.
- Moved conversion DTOs, helpers, queue worker glue, and seven route handlers into the split router.
- Kept upload preview queueing functional by importing the conversion enqueue helper into `file_router.py`.
- Added `test_file_conversion_router_contracts.py`.
- Updated existing conversion/upload/capabilities tests to patch the new module path.
- Registered the contract test in `.github/workflows/ci.yml`.
- Added this development and verification record.

## 3. Public API

Unchanged:

- `GET /api/v1/file/supported-formats`
- `GET /api/v1/file/{file_id}/conversion_summary`
- `POST /api/v1/file/{file_id}/convert`
- `GET /api/v1/file/conversion/{job_id}`
- `GET /api/v1/file/conversions/pending`
- `POST /api/v1/file/conversions/process`
- `POST /api/v1/file/process_cad`

Legacy `POST /api/v1/file/process_cad` still emits the same `Deprecation`, `Sunset`, and `Link` headers.

## 4. Contract Coverage

The new route ownership contract asserts:

- moved routes are owned by `file_conversion_router`;
- `file_router.py` no longer declares moved route decorators;
- `file_conversion_router` is registered before legacy `file_router`;
- moved routes are registered exactly once;
- File Management tag is preserved;
- generic metadata/download routes remain outside the conversion router.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

git diff --check

node --check playwright/tests/bom_obsolete_weight.spec.js
```

Results:

- py_compile: pass
- R1 file-router focused tests: 73 passed
- pact provider + doc-index + CI list contracts: 5 passed
- Playwright BOM obsolete/rollup smoke syntax check: pass
- `git diff --check`: pass

CI note:

- PR #383 first `playwright-esign` run failed twice on `bom_obsolete_weight.spec.js` with SQLite `database is locked`.
- The failure was outside the file conversion route split; remediation was limited to reusing the existing `postWithSqliteRetry` helper for the remaining mutating BOM obsolete/rollup smoke calls.

## 6. Non-Goals

- No upload route split.
- No attachment route split.
- No CAD/viewer artifact route split.
- No service-layer behavior changes.
- No schema, migration, settings, scheduler, shared-dev `142`, or UI changes.

## 7. Follow-Up

R2 should split CAD/viewer read routes only after R1 is merged and post-merge validation is green.
