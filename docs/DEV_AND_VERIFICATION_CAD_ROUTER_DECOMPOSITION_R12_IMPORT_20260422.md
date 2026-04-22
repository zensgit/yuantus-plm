# CAD Router Decomposition R12: Import

Date: 2026-04-22

## 1. Goal

Finish the CAD router decomposition by moving the final CAD import pipeline route out of `cad_router.py`.

R12 splits one public route without changing its path:

- `POST /api/v1/cad/import`

This is the last remaining route in the legacy aggregate router. The old `cad_router.py` is intentionally retained as an empty compatibility router so existing imports of `router as cad_router` keep working while ownership contracts continue to assert that split routers own the real CAD surface.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_import_router.py`.
- Moved CAD import DTOs, upload validation, checksum/mime helpers, CAD metadata resolution, auto Part creation helpers, duplicate-file repair guard, version-file edit guard, and `import_cad` into the new router.
- Registered `cad_import_router` in `src/yuantus/api/app.py` before the legacy compatibility `cad_router`.
- Reduced `src/yuantus/meta_engine/web/cad_router.py` to a zero-route compatibility shell.
- Updated CAD import tests to patch the new module path.

No public API path, method, request body, response field, auth dependency, quota behavior, storage key shape, auto Part creation behavior, attachment/version-file edit guard, CAD connector metadata resolution, dedup index payload, or job enqueueing behavior was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py`.
- Updated `src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py` to patch `cad_import_router`.
- Updated `src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py` to inspect `cad_import_router.py`.
- Added `cad_import_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new import route contract test to the CI contracts job list.
- Registered this delivery document in `docs/DELIVERY_DOC_INDEX.md`.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_import_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py \
  src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_diff_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_history_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py

git diff --check
```

Result:

- `py_compile`: passed
- Import lock guards + import router contracts + CI/doc contracts: `14 passed in 1.73s`
- CAD split router ownership contracts: `36 passed in 5.59s`
- Delivery doc index contracts: `3 passed in 0.03s`
- Pact provider verification: `1 passed in 11.50s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns `POST /cad/import`.
- `cad_router.py` no longer owns the import route.
- `create_app()` registers the moved import route exactly once.
- `cad_router.py` remains import-compatible as an empty aggregate shell.
- Import still depends on `get_current_user`, `get_db`, and `get_identity_db`.
- Upload validation still enforces max size and allowed extensions.
- Duplicate upload repair still runs `_ensure_duplicate_file_repair_editable` before rewriting a missing storage object.
- Existing attachment role updates still run current-version file edit guards.
- New attachment links still run current-version file edit guards.
- Auto Part creation still extracts CAD attributes before applying add/update AML.
- `create_bom_job` still requires an item id or auto-created Part.
- Preview, geometry, extract, BOM, dedup, and ML job enqueue payloads retain tenant/org/user/auth context.
- Dedup Vision still passes `"index": bool(dedup_index)` into the job payload.
- CI change-scope includes the new router file.

## 6. Follow-Up

R12 leaves the CAD aggregate router with zero owned routes. Any future cleanup should treat removal of `cad_router.py` registration/import compatibility as a separate bounded change because multiple ownership contract tests still import it to prove route migration remains complete.
