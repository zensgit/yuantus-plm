# CAD Router Decomposition R5: Mesh Stats

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition with the smallest pact-covered read endpoint.

R5 splits one public contract without changing its path:

- `GET /api/v1/cad/files/{file_id}/mesh-stats`

This endpoint was chosen before `properties`, `view-state`, `review`, `diff`, and `history` because it is read-only and does not mutate CAD state, enqueue preview jobs, or write change-log rows.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_mesh_stats_router.py`.
- Moved `CadMeshStatsResponse`, `_load_cad_metadata_payload()`, `_extract_mesh_stats()`, and `get_cad_mesh_stats()` into the new router.
- Registered `cad_mesh_stats_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTO, metadata loader, mesh extraction helper, and endpoint from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, auth dependency, metadata download behavior, unavailable-metadata fallback, or invalid-JSON error behavior was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_mesh_stats_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py`.
- Updated the existing payload helper test to import `_load_cad_metadata_payload()` from the split router.
- Added `cad_mesh_stats_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new mesh route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_mesh_stats_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_mesh_stats_router.py \
  src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_router_payload_helpers.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py \
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

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Result:

- `py_compile`: passed
- Focused R1/R2/R3/R4/R5 regression and contracts: `61 passed in 4.66s`
- Pact provider verification: `1 passed in 12.24s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns `/cad/files/{file_id}/mesh-stats`.
- `cad_router.py` no longer owns `/cad/files/{file_id}/mesh-stats`.
- `create_app()` registers the route exactly once.
- Missing file still returns 404.
- Missing metadata path still returns `available=false` with `CAD metadata not available`.
- Attribute-only metadata still returns `available=false` with `CAD mesh metadata not available`.
- Non-mesh metadata still returns sorted `raw_keys`.
- Mesh metadata still returns entity count, triangle count, bounds, raw keys, and `available=true`.
- Invalid metadata JSON still returns HTTP 500 with `CAD metadata invalid JSON`.
- CI change-scope includes the new router file.

## 6. Follow-Up

Remaining CAD file endpoints are more coupled:

- `properties`: read/write pair, pact-covered.
- `view-state`: read/write pair, validates CAD document payload, can enqueue preview jobs.
- `review`: read/admin-write pair, writes CAD change logs.
- `diff`: read-only but depends on properties semantics.
- `history`: read-only but depends on change-log model and write endpoints.

Split the next slice only with pact-surface focused tests and route ownership contracts.
