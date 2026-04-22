# CAD Router Decomposition R2: Connectors

Date: 2026-04-22

## 1. Goal

Continue CAD router decomposition by moving the connector discovery and reload surface out of the remaining `cad_router.py`.

R2 splits 2 public contracts without changing paths:

- `GET /api/v1/cad/connectors`
- `POST /api/v1/cad/connectors/reload`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/cad_connectors_router.py`.
- Moved connector DTOs and the 2 connector handlers into the new router.
- Registered `cad_connectors_router` in `src/yuantus/api/app.py` before the remaining `cad_router`.
- Removed the moved handlers, DTOs, and `reload_connectors` import from `src/yuantus/meta_engine/web/cad_router.py`.

No public API path, method, response shape, reload semantics, or admin permission boundary was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_cad_connectors_router.py`.
- Added `src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py`.
- Added `cad_connectors_router.py` to the CI pact/provider CAD surface change trigger.
- Added the new connector route contract test to the CI contracts job list.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_router.py \
  src/yuantus/meta_engine/web/cad_connectors_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_connectors_router.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py \
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
- Focused R1/R2 regression and contracts: `31 passed in 3.37s`
- `git diff --check`: passed

## 5. Review Checklist

- The split router owns both connector route contracts.
- `cad_router.py` no longer owns `/cad/connectors` or `/cad/connectors/reload`.
- `create_app()` registers each moved route exactly once.
- `GET /cad/connectors` keeps sorted connector metadata behavior.
- `POST /cad/connectors/reload` keeps admin-only dependency and path-override guard.
- CI change-scope includes the new router file.

## 6. Follow-Up

Continue CAD router decomposition with `/cad/sync-template/*` before touching larger import/checkin/file metadata paths.
