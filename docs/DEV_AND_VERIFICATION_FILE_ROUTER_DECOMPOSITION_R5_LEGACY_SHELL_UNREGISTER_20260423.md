# File Router Decomposition R5 Legacy Shell Unregister - Development And Verification

Date: 2026-04-23

## 1. Goal

Remove the empty legacy `file_router` shell from runtime app registration after R1-R4 moved all public `/api/v1/file/*` handlers into focused routers.

## 2. Delivered

- Removed `file_router` import and `app.include_router(file_router, ...)` from `src/yuantus/api/app.py`.
- Kept `src/yuantus/meta_engine/web/file_router.py` as an empty compatibility module for downstream imports.
- Added `test_file_router_shell_contracts.py` to prove the shell declares no runtime routes and is not registered in the app.
- Retargeted existing file router registration-order contracts to assert ordering between active split routers instead of the legacy shell.
- Removed the obsolete `file_router` include from `test_cad_capabilities_router.py`.
- Updated the check-in service comment to point to `file_storage_router`.
- Registered the shell contract in `.github/workflows/ci.yml`.

## 3. Public API

Unchanged. The active file router registration order is now:

- `file_conversion_router`
- `file_viewer_router`
- `file_storage_router`
- `file_attachment_router`
- `file_metadata_router`

The legacy `file_router` module remains importable but has no decorators and is not registered in `create_app()`.

## 4. Contract Coverage

The new and updated contracts assert:

- legacy `file_router.py` has no `@file_router.*` runtime route decorators;
- `create_app()` no longer imports or registers `file_router`;
- active split routers are registered in the expected order;
- existing moved-route ownership contracts still register each public `/api/v1/file/*` endpoint exactly once.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/meta_engine/web/file_viewer_router.py \
  src/yuantus/meta_engine/web/file_storage_router.py \
  src/yuantus/meta_engine/web/file_attachment_router.py \
  src/yuantus/meta_engine/web/file_metadata_router.py \
  src/yuantus/meta_engine/services/checkin_service.py \
  src/yuantus/meta_engine/tests/test_file_router_shell_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_router_shell_contracts.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_attachment_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_metadata_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

git diff --check
```

Results:

- py_compile: pass
- active file-router ownership contracts: 41 passed
- adjacent file-router regression + pact/doc/CI contracts: 49 passed
- doc-index + CI-list contracts: 4 passed
- `git diff --check`: pass

## 6. Non-Goals

- No deletion of `src/yuantus/meta_engine/web/file_router.py`.
- No public URL changes.
- No response schema changes.
- No service-layer behavior changes.
- No schema, migration, settings, scheduler, shared-dev `142`, or UI changes.

## 7. Follow-Up

The `file_router.py` compatibility module can be deleted later only after historical scripts, docs, and external import consumers are intentionally migrated.
