# CAD Router Decomposition R7: Review

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the pact-covered CAD review read/write pair out of the remaining `cad_router.py`.

R7 splits two public contracts without changing paths:

- `GET /api/v1/cad/files/{file_id}/review`
- `POST /api/v1/cad/files/{file_id}/review`

The endpoints were split as a pair because the read and write contracts share the same response DTO and persisted `FileContainer.cad_review*` fields.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_review_router.py`.
- Moved `CadReviewResponse`, `CadReviewRequest`, `get_cad_review()`, and `update_cad_review()` into the new router.
- Reused `src/yuantus/meta_engine/web/cad_change_log.py` for `cad_review_update` audit entries.
- Registered `cad_review_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTOs and handlers from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, auth dependency, allowed-state validation, state normalization, commit behavior, or CAD change-log payload was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_review_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py`.
- Added `cad_review_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new review route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_review_router.py \
  src/yuantus/meta_engine/web/cad_change_log.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
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
- Focused R1/R2/R3/R4/R5/R6/R7 regression and contracts: `79 passed in 5.43s`
- Pact provider verification: `1 passed in 13.42s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns GET/POST `/cad/files/{file_id}/review`.
- `cad_router.py` no longer owns the review route pair.
- `create_app()` registers each moved route exactly once.
- GET still returns existing review state, note, reviewed timestamp, and reviewer id.
- GET missing file still returns 404.
- POST still requires admin dependency.
- POST still normalizes state with strip/lower and only accepts `pending`, `approved`, or `rejected`.
- POST invalid state still returns 400 without add/commit side effects.
- POST still writes `cad_review_update` with `{"state": state, "note": note}` and commits the file container.
- CI change-scope includes the new router file.
- Pact provider verification passes for the Wave 5 CAD review contracts.

## 6. Follow-Up

Remaining CAD file endpoints:

- `view-state`: read/write pair, validates CAD document payload, can enqueue preview jobs.
- `diff`: read-only but depends on properties semantics.
- `history`: read-only but depends on CAD change-log model and write endpoints.

Split `view-state` only after isolating its CAD document payload helper and preview job side effect tests. `diff` and `history` can follow as lower-risk read slices once the write-heavy routes are stable.
