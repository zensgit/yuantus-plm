# CAD Router Decomposition R8: Diff

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the pact-covered CAD property diff endpoint out of the remaining `cad_router.py`.

R8 splits one public contract without changing its path:

- `GET /api/v1/cad/files/{file_id}/diff`

This endpoint was chosen before `view-state` because it is read-only and has no CAD document validation, preview job enqueue, or change-log write side effects.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_diff_router.py`.
- Moved `CadDiffResponse`, `_diff_dicts()`, and `diff_cad_properties()` into the new router.
- Registered `cad_diff_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTO, helper, and handler from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, auth dependency, query parameter behavior, 422 missing-target behavior, 404 missing-file behavior, or diff algorithm was intentionally changed.

## 3. Test Changes

- Updated `src/yuantus/meta_engine/tests/test_cad_diff_query_alias.py` to exercise the split router.
- Added `src/yuantus/meta_engine/tests/test_cad_diff_router_contracts.py`.
- Added `cad_diff_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new diff route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_diff_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
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
- Focused R1/R2/R3/R4/R5/R6/R7/R8 regression and contracts: `87 passed in 5.93s`
- Pact provider verification: `1 passed in 11.88s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns GET `/cad/files/{file_id}/diff`.
- `cad_router.py` no longer owns the diff route.
- `create_app()` registers the moved route exactly once.
- Canonical `other_file_id` query parameter still works.
- Legacy `other_id` query alias still works.
- `other_file_id` still takes precedence when both query params are present.
- Missing compare target still returns 422 with `other_file_id is required`.
- Missing source or target file still returns 404 with `File not found`.
- Diff response still reports added, removed, changed, and schema-version from/to values.
- CI change-scope includes the new router file.
- Pact provider verification passes for the Wave 5 CAD diff contract.

## 6. Follow-Up

Remaining CAD file endpoints:

- `view-state`: read/write pair, validates CAD document payload, can enqueue preview jobs.
- `history`: read-only but depends on CAD change-log model and write endpoints.

Split `history` next if the goal is another low-risk read slice. Split `view-state` last because it has validation and preview job side effects.
