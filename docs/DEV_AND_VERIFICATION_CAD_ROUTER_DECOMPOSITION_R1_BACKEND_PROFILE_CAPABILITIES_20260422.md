# CAD Router Decomposition R1: Backend Profile And Capabilities

Date: 2026-04-22

## 1. Goal

Start the CAD router decomposition line by moving the low-coupling backend profile and capabilities read surface out of the 2500-line `cad_router.py`.

R1 splits 4 public contracts without changing paths:

- `GET /api/v1/cad/backend-profile`
- `PUT /api/v1/cad/backend-profile`
- `DELETE /api/v1/cad/backend-profile`
- `GET /api/v1/cad/capabilities`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_backend_profile_router.py`.
- Moved backend profile DTOs, capabilities DTOs, scoped profile resolution, feature status helpers, and the 4 handlers into the new router.
- Registered `cad_backend_profile_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved handlers and imports from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, schema, persistence behavior, authentication dependency, or admin permission boundary was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py`.
- Retargeted backend profile and capabilities router tests from `cad_router` to `cad_backend_profile_router`.
- Added `cad_backend_profile_router.py` to the CI change-scope contract trigger for pact/provider CAD surface changes.
- Added the new contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_backend_profile_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
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
- Focused regression and contracts: `24 passed in 3.23s`

## 5. Review Checklist

- The split router owns all backend profile and capabilities route contracts.
- `cad_router.py` no longer owns `/cad/backend-profile` or `/cad/capabilities`.
- `create_app()` registers each moved route exactly once.
- Existing backend profile auth behavior remains unchanged: GET requires an authenticated user; PUT/DELETE require admin.
- Existing capabilities response contracts remain unchanged, including scoped backend profile override behavior and STEP/IGES backend metadata.
- CI change-scope includes the new router file.

## 6. Follow-Up

Continue CAD router decomposition with another low-coupling group, such as `/cad/connectors*` or `/cad/sync-template/*`, before touching large import/checkin paths.
