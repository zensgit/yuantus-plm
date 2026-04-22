# CAD Router Decomposition R6: Properties

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the pact-covered CAD properties read/write pair out of the remaining `cad_router.py`.

R6 splits two public contracts without changing paths:

- `GET /api/v1/cad/files/{file_id}/properties`
- `PATCH /api/v1/cad/files/{file_id}/properties`

The endpoints were split as a pair because the read and write contracts share the same response DTO and persisted `FileContainer.cad_properties*` fields.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_properties_router.py`.
- Moved `CadPropertiesResponse`, `CadPropertiesUpdateRequest`, `get_cad_properties()`, and `update_cad_properties()` into the new router.
- Added `src/yuantus/meta_engine/web/cad_change_log.py` as a shared helper for CAD change log writes.
- Updated remaining `cad_router.py` write paths to reuse `log_cad_change()` through the existing `_log_cad_change` alias.
- Registered `cad_properties_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved DTOs and handlers from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, auth dependency, source normalization, commit behavior, or CAD change-log payload was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_properties_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py`.
- Added `cad_properties_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new properties route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_properties_router.py \
  src/yuantus/meta_engine/web/cad_change_log.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
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
- Focused R1/R2/R3/R4/R5/R6 regression and contracts: `70 passed in 5.07s`
- Pact provider verification: `1 passed in 11.76s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns GET/PATCH `/cad/files/{file_id}/properties`.
- `cad_router.py` no longer owns the properties route pair.
- `create_app()` registers each moved route exactly once.
- GET still returns existing properties, updated timestamp, source, and schema version.
- GET missing file still returns 404.
- PATCH still replaces properties, normalizes blank source to `manual`, writes `cad_properties_updated_at`, logs `cad_properties_update`, adds the file container, and commits.
- PATCH missing file still returns 404.
- Existing view-state and review write paths still call the same CAD change-log helper semantics through `_log_cad_change`.
- CI change-scope includes the new router file.
- Pact provider verification passes for the Wave 5 CAD properties contracts.

## 6. Follow-Up

Remaining CAD file endpoints are more coupled:

- `view-state`: read/write pair, validates CAD document payload, can enqueue preview jobs.
- `review`: read/admin-write pair, writes CAD change logs.
- `diff`: read-only but depends on properties semantics.
- `history`: read-only but depends on CAD change-log model and write endpoints.

Split the next slice only with pact-surface focused tests and route ownership contracts.
