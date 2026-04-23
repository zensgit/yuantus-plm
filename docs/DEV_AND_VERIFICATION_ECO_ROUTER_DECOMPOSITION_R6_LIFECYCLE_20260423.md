# ECO Router Decomposition R6: Lifecycle

Date: 2026-04-23

## 1. Scope

R6 moves ECO lifecycle action endpoints out of legacy `eco_router.py` into a dedicated router:

- `POST /api/v1/eco/{eco_id}/cancel`
- `GET /api/v1/eco/{eco_id}/unsuspend-diagnostics`
- `POST /api/v1/eco/{eco_id}/suspend`
- `POST /api/v1/eco/{eco_id}/unsuspend`
- `POST /api/v1/eco/{eco_id}/move-stage`

The public paths, request parameters, response shapes, auth dependencies, and `ECO` tag are preserved.

## 2. Non-Goals

- No ECO CRUD relocation.
- No kanban, bind-product, or new-revision relocation.
- No approval, dashboard, impact/apply, or change-analysis relocation; those are sealed by R1-R5.
- No service-layer behavior changes.
- No schema, migration, scheduler, or shared-dev changes.

## 3. Implementation

- Added `src/yuantus/meta_engine/web/eco_lifecycle_router.py`.
- Registered `eco_lifecycle_router` after `eco_change_analysis_router` and before legacy `eco_router`.
- Moved `MoveStageRequest`, `SuspendRequest`, `UnsuspendRequest`, and `_ensure_can_unsuspend_eco` into the lifecycle router.
- Removed the five moved lifecycle handlers from `eco_router.py`.
- Retargeted existing suspend/unsuspend tests to patch `eco_lifecycle_router.ECOService`.
- Added `test_eco_lifecycle_router.py` for cancel and move-stage behavior coverage.
- Added `test_eco_lifecycle_router_contracts.py` for route ownership, no legacy leakage, registration order, tag preservation, and scope boundary checks.
- Added the new router and contract test to `.github/workflows/ci.yml`.

## 4. Verification

Commands run locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/meta_engine/web/eco_lifecycle_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: `29 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router.py \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router.py
```

Result: `154 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `6 passed`.

```bash
git diff --check
```

Result: passed.

## 5. Review Checklist

- The moved endpoints are owned by `yuantus.meta_engine.web.eco_lifecycle_router`.
- Legacy `eco_router.py` no longer declares the moved lifecycle decorators.
- `eco_lifecycle_router` is registered before legacy `eco_router`, so parameterized legacy routes cannot shadow the moved endpoints.
- R1-R5 routers remain sealed.
- CRUD, kanban, bind-product, and new-revision remain outside this slice.
- Public API route paths are unchanged.
