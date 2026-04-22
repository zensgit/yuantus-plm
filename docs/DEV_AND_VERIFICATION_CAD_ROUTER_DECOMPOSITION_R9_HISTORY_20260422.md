# CAD Router Decomposition R9: History

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the pact-covered CAD change history read endpoint out of the remaining `cad_router.py`.

R9 splits one public contract without changing its path:

- `GET /api/v1/cad/files/{file_id}/history`

This endpoint was chosen before `view-state` because it is read-only and has no CAD document validation, preview job enqueue, or state mutation side effects.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_history_router.py`.
- Moved `CadChangeLogEntry`, `CadChangeLogResponse`, and `get_cad_history()` into the new router.
- Registered `cad_history_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTOs and handler from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, auth dependency, limit validation, query ordering, payload fallback, or 404 behavior was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_history_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_history_router_contracts.py`.
- Added `cad_history_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new history route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_history_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_history_router.py \
  src/yuantus/meta_engine/tests/test_cad_history_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_diff_query_alias.py \
  src/yuantus/meta_engine/tests/test_cad_diff_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_review_router.py \
  src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py \
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
- Focused R1/R2/R3/R4/R5/R6/R7/R8/R9 regression and contracts: `94 passed in 6.03s`
- Pact provider verification: `1 passed in 12.66s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns GET `/cad/files/{file_id}/history`.
- `cad_router.py` no longer owns the history route.
- `create_app()` registers the moved route exactly once.
- Missing file still returns 404 before querying `CadChangeLog`.
- `limit` still defaults to 50 and remains bounded by FastAPI `ge=1, le=200`.
- The query still filters by `file_id`, orders `created_at` descending, applies the limit, and returns all rows.
- Entry payload still falls back to `{}` when stored payload is null.
- Entry timestamps still use `isoformat()`.
- CI change-scope includes the new router file.
- Pact provider verification passes for the Wave 5 CAD history contract.

## 6. Follow-Up

The only remaining CAD file endpoint group in `cad_router.py` is `view-state`.

Split `view-state` last because it combines read/write behavior, CAD document payload validation, CAD entity note normalization, optional preview job enqueue, quota error handling, and CAD change-log writes.
