# CAD Router Decomposition R10: View State

Date: 2026-04-22

## 1. Goal

Finish the CAD file-endpoint decomposition by moving the view-state read/write endpoints out of the remaining `cad_router.py`.

R10 splits two public routes without changing their paths:

- `GET /api/v1/cad/files/{file_id}/view-state`
- `PATCH /api/v1/cad/files/{file_id}/view-state`

This slice was intentionally left until after R9 because it includes state mutation, CAD document entity validation, CAD change-log writes, and optional preview job enqueue.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_view_state_router.py`.
- Moved `CadEntityNote`, `CadViewStateResponse`, `CadViewStateUpdateRequest`, CAD document payload loading, entity-id validation, note normalization, and the two view-state handlers into the new router.
- Registered `cad_view_state_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTOs, helpers, and handlers from `src/yuantus/meta_engine/web/cad_router.py`.
- Updated the CAD document payload helper test to patch the new module path.

No public API path, method, response model field, auth dependency, 404 behavior, entity validation behavior, audit action name, preview job payload, preview job priority, dedupe flag, or quota exception mapping was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_view_state_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py`.
- Added `cad_view_state_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new view-state route contract test to the CI contracts job list.
- Registered this delivery document in `docs/DELIVERY_DOC_INDEX.md`.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_view_state_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_view_state_router.py \
  src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py \
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
- Focused R1/R2/R3/R4/R5/R6/R7/R8/R9/R10 regression and contracts: `106 passed in 7.28s`
- Pact provider verification: `1 passed in 13.73s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns GET/PATCH `/cad/files/{file_id}/view-state`.
- `cad_router.py` no longer owns the view-state routes.
- `create_app()` registers the moved routes exactly once.
- Missing file still returns 404 before mutation or query-side effects.
- GET still returns existing hidden ids, notes, source, updated timestamp, and CAD document schema version.
- PATCH still preserves omitted hidden ids and notes from the existing state.
- PATCH still normalizes notes through the response model and stores JSON-compatible note dictionaries.
- PATCH still validates hidden/note entity ids against the CAD document payload when a document exists.
- Unknown CAD entity ids still return HTTP 400 and do not commit.
- PATCH still writes `cad_view_state_update` to the CAD change log.
- PATCH with `refresh_preview=true` still enqueues `cad_preview` only for CAD files.
- Preview enqueue still uses priority 15, `dedupe=True`, and the same tenant/org/user payload.
- `QuotaExceededError` from preview enqueue still maps to the original HTTP status and detail payload.
- CI change-scope includes the new router file.
- Pact provider verification covers the unchanged Wave 5 view-state contract.

## 6. Follow-Up

After R10, the CAD file endpoint groups that were explicitly targeted in the decomposition cycle have been split out. Any further reduction of `cad_router.py` should be handled as a new bounded cycle because the remaining handlers are larger import/checkin/checkout flows rather than small file-read/write endpoint groups.
