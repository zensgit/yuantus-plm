# CAD Router Decomposition R11: Checkin

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition after R10 by moving the CAD checkout/checkin/status lifecycle routes out of the remaining `cad_router.py`.

R11 splits four public routes without changing their paths:

- `POST /api/v1/cad/{item_id}/checkout`
- `POST /api/v1/cad/{item_id}/undo-checkout`
- `POST /api/v1/cad/{item_id}/checkin`
- `GET /api/v1/cad/{item_id}/checkin-status`

This slice keeps the import endpoint untouched. It is the smallest coherent lifecycle group left after the file endpoint decomposition.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_checkin_router.py`.
- Moved `get_checkin_manager`, checkin URL helpers, conversion-job aggregation helpers, checkin DTOs, checkout, undo-checkout, checkin, and checkin-status handlers into the new router.
- Registered `cad_checkin_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved helpers, DTOs, imports, and handlers from `src/yuantus/meta_engine/web/cad_router.py`.
- Updated checkin-status tests to patch the new module path.

No public API path, method, request body, response field, auth dependency, quota behavior, checkin manager behavior, conversion-job filtering, viewer-readiness assessment, or status URL shape was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py`.
- Updated `src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py` to import/patch `cad_checkin_router`.
- Added `cad_checkin_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new checkin route contract test to the CI contracts job list.
- Registered this delivery document in `docs/DELIVERY_DOC_INDEX.md`.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_checkin_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py

YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py
```

Result:

- `py_compile`: passed
- Focused checkin/router contracts/doc contracts: `10 passed in 1.87s` and `6 passed in 0.03s`
- Wider CAD router decomposition + checkin adjacent regression: `120 passed in 7.21s`
- Pact provider verification: `1 passed in 12.55s`
- CAD import lock-guard adjacent check under optional local auth: `4 passed in 2.68s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns checkout, undo-checkout, checkin, and checkin-status routes.
- `cad_router.py` no longer owns these checkin lifecycle routes.
- `create_app()` registers each moved route exactly once.
- `get_checkin_manager` still depends on `get_current_user` and `get_db`.
- Checkout still commits on success and rolls back on errors.
- Undo-checkout still commits on success and preserves its existing ValueError mapping.
- Checkin still evaluates file/storage quota before calling `CheckinManager.checkin`.
- Checkin still rolls back on `ValueError`, `HTTPException`, and generic exception paths.
- Checkin response still includes status URL and file status URL with unchanged route names.
- Checkin-status still rejects missing item/version/native file links with 404.
- Checkin-status still prefers anchored conversion job ids when present.
- Checkin-status still summarizes pending/processing/completed/failed jobs and assesses viewer readiness.
- CI change-scope includes the new router file.
- Pact provider verification remains green for unchanged CAD contracts.

## 6. Follow-Up

After R11, the remaining `cad_router.py` responsibility is the CAD import pipeline plus its import-specific helpers. Splitting import should be treated as a separate high-risk bounded PR because it touches file storage, dedupe repair, quota evaluation, auto Part creation, attachment/version-file edit guards, connector metadata, and job enqueueing.
