# CAD Router Decomposition R3: Sync Template

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the CAD property sync-template surface out of the remaining `cad_router.py`.

R3 splits 2 public contracts without changing paths:

- `GET /api/v1/cad/sync-template/{item_type_id}`
- `POST /api/v1/cad/sync-template/{item_type_id}`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_sync_template_router.py`.
- Moved sync-template DTOs, `_csv_bool()`, CSV/JSON template generation, and CSV upload apply logic into the new router.
- Registered `cad_sync_template_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved handlers, DTOs, and CSV/StringIO imports from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, CSV column contract, admin permission boundary, `properties_schema` invalidation, or commit behavior was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_sync_template_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_router_payload_helpers.py` after CI caught the remaining CAD metadata/document payload helpers still depend on `io.BytesIO()`.
- Added `cad_sync_template_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new sync-template route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_sync_template_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_router_payload_helpers.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `py_compile`: passed
- Focused R1/R2/R3 regression and contracts: `43 passed in 4.01s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns both sync-template route contracts.
- `cad_router.py` no longer owns `/cad/sync-template/{item_type_id}`.
- `create_app()` registers each moved route exactly once.
- GET keeps both JSON response and CSV attachment behavior.
- POST keeps `property_name`/`name` and `cad_key`/`cad_attribute` aliases.
- POST keeps `properties_schema = None` invalidation and commits exactly as before.
- CI change-scope includes the new router file.

## 6. Follow-Up

Continue CAD router decomposition with a new bounded slice. Avoid import/checkin first; consider file metadata or attribute read surfaces only if tests can isolate them cleanly.
