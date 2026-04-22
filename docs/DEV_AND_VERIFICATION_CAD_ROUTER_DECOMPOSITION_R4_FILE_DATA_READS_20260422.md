# CAD Router Decomposition R4: File Data Reads

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the lowest-coupling CAD file data read endpoints out of the remaining `cad_router.py`.

R4 splits 2 public contracts without changing paths:

- `GET /api/v1/cad/files/{file_id}/attributes`
- `GET /api/v1/cad/files/{file_id}/bom`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_file_data_router.py`.
- Moved `CadExtractAttributesResponse`, `CadBomResponse`, and the 2 read-only handlers into the new router.
- Registered `cad_file_data_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTOs and handlers from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, auth dependency, persisted-payload behavior, or conversion-job fallback behavior was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_file_data_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py`.
- Added `cad_file_data_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new file-data route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_file_data_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_file_data_router.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py \
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
- Focused R1/R2/R3/R4 regression and contracts: `52 passed in 4.69s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns both moved file-data route contracts.
- `cad_router.py` no longer owns `/cad/files/{file_id}/attributes` or `/cad/files/{file_id}/bom`.
- `create_app()` registers each moved route exactly once.
- Attributes read still prefers persisted `FileContainer.cad_attributes`.
- Attributes read still falls back to matching `cad_extract` conversion job payload.
- BOM read still prefers persisted `cad_bom_path` JSON.
- BOM read still falls back to matching `cad_bom` conversion job payload.
- CI change-scope includes the new router file.

## 6. Follow-Up

Next CAD decomposition slice should be chosen carefully. `properties`, `view-state`, `review`, `diff`, `history`, and `mesh-stats` are pact-covered and more tightly coupled to writes/change logs; split them only with corresponding pact-surface focused tests.
