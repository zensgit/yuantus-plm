# Residual Router Exception Chaining Closeout - Development and Verification

Date: 2026-05-14

## 1. Goal

Close the final residual bare `HTTPException(... detail=str(e))` mappings in
`src/yuantus/meta_engine/web` and `src/yuantus/api`, after the earlier
Approval, Document Sync, Quality, Box, Maintenance, Subcontracting, Locale,
Tail, BOM, Version, ECO, and File closeouts.

API callers keep the same status codes and detail strings. Logs and debuggers
now retain the original exception through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/cad_checkin_router.py`
- `src/yuantus/meta_engine/web/change_router.py`
- `src/yuantus/meta_engine/web/equivalent_router.py`
- `src/yuantus/meta_engine/web/schema_router.py`
- `src/yuantus/meta_engine/web/store_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `src/yuantus/meta_engine/tests/test_schema_router.py`

Added:

- `src/yuantus/meta_engine/tests/test_residual_router_exception_chaining_closeout.py`
- `docs/DEV_AND_VERIFICATION_RESIDUAL_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md`

## 3. Behavior

Changed paths cover the remaining residual surfaces:

- CAD checkout / undo-checkout / checkin failure handling
- legacy ECM affected-item and execute compatibility failures
- app store purchase/install failures
- equivalent relationship removal failures
- schema refresh and schema lookup failures

Failure responses remain unchanged:

```text
400 <original exception text>
404 <original exception text>
500 <original exception text>
```

Existing transaction behavior is preserved. Paths that rolled back before still
roll back. Existing paths without rollback on a specific exception class remain
unchanged; this closeout only adds exception chaining.

## 4. Contract Coverage

The new contract verifies:

- representative runtime paths preserve the original exception as
  `HTTPException.__cause__`
- response status/detail semantics remain unchanged
- rollback behavior stays pinned for representative write paths
- source-level expected `from e` conversions remain pinned
- `src/yuantus/meta_engine/web` and `src/yuantus/api` have no remaining bare
  stringified `HTTPException` mappings
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, response shape, or public API change.
- No service, auth, permission, quota, CAD, schema, legacy ECM, app-store, or
  transaction helper change.
- No Phase 5, P3.4 cutover, CAD plugin, scheduler, ECO, File, BOM, or Version
  work.

## 5.1 Test Hygiene

`test_schema_router.py` now sets `AUTH_MODE=optional` with the same local test
fixture pattern used by adjacent router tests. That test file overrides DB
dependencies and is meant to validate schema-router behavior, not middleware
authentication.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_checkin_router.py \
  src/yuantus/meta_engine/web/change_router.py \
  src/yuantus/meta_engine/web/equivalent_router.py \
  src/yuantus/meta_engine/web/schema_router.py \
  src/yuantus/meta_engine/web/store_router.py \
  src/yuantus/meta_engine/tests/test_residual_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_schema_router.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_residual_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_schema_router.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

rg -n --pcre2 "raise HTTPException\\([^\\n]*detail=str\\((?:e|exc)\\)\\)(?! from )" \
  src/yuantus/meta_engine/web src/yuantus/api

git diff --check
```

Results:

- `py_compile`: passed
- focused residual exception-chaining + adjacent router suites: `26 passed`
- doc-index / CI list quartet: `5 passed`
- boot check: `routes=676 middleware=4`
- global bare stringified exception scan: no matches
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all touched residual paths use `from e`.
- Confirm rollback behavior remains unchanged.
- Confirm no bare `detail=str(e|exc)` mappings remain in `src/yuantus/meta_engine/web`
  or `src/yuantus/api`.
- Confirm CI and doc-index entries are present and sorted.
