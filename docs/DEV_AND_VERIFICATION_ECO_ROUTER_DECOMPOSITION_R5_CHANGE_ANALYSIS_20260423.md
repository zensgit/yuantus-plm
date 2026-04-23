# ECO Router Decomposition R5: Change Analysis

Date: 2026-04-23

## 1. Scope

R5 moves ECO change-analysis and conflict-diagnostics endpoints out of legacy `eco_router.py` into a dedicated router:

- `GET /api/v1/eco/{eco_id}/routing-changes`
- `POST /api/v1/eco/{eco_id}/compute-routing-changes`
- `GET /api/v1/eco/{eco_id}/changes`
- `POST /api/v1/eco/{eco_id}/compute-changes`
- `GET /api/v1/eco/{eco_id}/conflicts`

The public paths, request parameters, response shapes, and `ECO` tag are preserved.

## 2. Non-Goals

- No ECO CRUD relocation.
- No lifecycle relocation: cancel, suspend, unsuspend, unsuspend-diagnostics, and move-stage remain in legacy `eco_router.py`.
- No impact/apply relocation; that is sealed by R4.
- No service-layer behavior changes.
- No schema, migration, scheduler, or shared-dev changes.

## 3. Implementation

- Added `src/yuantus/meta_engine/web/eco_change_analysis_router.py`.
- Registered `eco_change_analysis_router` after `eco_impact_apply_router` and before legacy `eco_router`.
- Removed the five moved change-analysis handlers from `eco_router.py`.
- Retargeted existing compute/routing tests to patch `eco_change_analysis_router.ECOService`.
- Added `test_eco_change_analysis_router.py` for BOM changes and conflicts behavior coverage.
- Added `test_eco_change_analysis_router_contracts.py` for route ownership, no legacy leakage, registration order, tag preservation, and scope boundary checks.
- Added the new router and contract test to `.github/workflows/ci.yml`.

## 4. Verification

Commands run locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/meta_engine/web/eco_change_analysis_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router.py \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: `55 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router.py \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py
```

Result: `144 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `5 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

Result: `3 passed`.

```bash
git diff --check
```

Result: passed after removing one trailing blank line in `eco_router.py`.

## 5. Review Checklist

- The moved endpoints are owned by `yuantus.meta_engine.web.eco_change_analysis_router`.
- Legacy `eco_router.py` no longer declares the moved change-analysis decorators.
- `eco_change_analysis_router` is registered before legacy `eco_router`, so parameterized legacy routes cannot shadow the moved endpoints.
- R4 impact/apply endpoints remain in `eco_impact_apply_router`.
- Lifecycle and CRUD endpoints remain outside this slice.
- Public API route paths are unchanged.
