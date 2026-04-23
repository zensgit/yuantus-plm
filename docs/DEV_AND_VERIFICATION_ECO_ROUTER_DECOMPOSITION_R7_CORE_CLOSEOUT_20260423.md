# ECO Router Decomposition R7: Core Closeout

Date: 2026-04-23

## 1. Scope

R7 is the final ECO router decomposition slice. It moves the last core ECO endpoints out of the legacy `eco_router.py` module into `eco_core_router.py`:

- `GET /api/v1/eco/kanban`
- `POST /api/v1/eco`
- `GET /api/v1/eco`
- `GET /api/v1/eco/{eco_id}`
- `POST /api/v1/eco/{eco_id}/bind-product`
- `PUT /api/v1/eco/{eco_id}`
- `DELETE /api/v1/eco/{eco_id}`
- `POST /api/v1/eco/{eco_id}/new-revision`

The public paths, request/response shapes, auth dependencies, and `ECO` tag are preserved.

## 2. Non-Goals

- No service-layer behavior changes.
- No approval, stage, workflow, impact/apply, change-analysis, or lifecycle changes; R1-R6 stay sealed.
- No schema, migration, scheduler, shared-dev, or UI changes.
- No removal of the `eco_router.py` module path; it remains as a compatibility shim.

## 3. Implementation

- Added `src/yuantus/meta_engine/web/eco_core_router.py`.
- Converted `src/yuantus/meta_engine/web/eco_router.py` into a compatibility shim that re-exports `eco_core_router` as `eco_router`.
- Updated `src/yuantus/api/app.py` to import and register `eco_core_router` after `eco_lifecycle_router`.
- Added `test_eco_core_router.py` for behavior coverage across kanban, CRUD, bind-product, delete, and new-revision endpoints.
- Added `test_eco_core_router_contracts.py` for route ownership, one-time app registration, shim cleanliness, registration order, tag preservation, split-scope boundaries, and static-before-dynamic route order.
- Updated existing R1-R6 contract tests to use `eco_core_router` as the final registration boundary.
- Added the new router and contract test to `.github/workflows/ci.yml`.

## 4. Verification

Commands run locally before PR:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/meta_engine/web/eco_core_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_core_router.py \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_core_router.py
```

Result: `17 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router.py \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router.py \
  src/yuantus/meta_engine/tests/test_eco_core_router.py
```

Result: `171 passed`.

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

- The final core endpoints are owned by `yuantus.meta_engine.web.eco_core_router`.
- `eco_router.py` no longer declares any FastAPI route decorators.
- `eco_core_router` is registered after all specialized ECO routers.
- `/kanban` remains declared before `/{eco_id}`.
- R1-R6 routers remain sealed and do not absorb core endpoints.
- Public API route paths are unchanged.

## 6. Closeout Status

Local pre-PR verification is complete. PR CI and post-merge verification are recorded in the final handoff after merge.
