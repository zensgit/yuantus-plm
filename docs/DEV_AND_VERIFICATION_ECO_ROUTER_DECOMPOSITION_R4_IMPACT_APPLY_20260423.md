# ECO Router Decomposition R4: Impact Apply

Date: 2026-04-23

## 1. Scope

R4 moves the ECO impact and apply surface out of the legacy `eco_router.py` into a dedicated router:

- `GET /api/v1/eco/{eco_id}/impact`
- `GET /api/v1/eco/{eco_id}/impact/export`
- `GET /api/v1/eco/{eco_id}/bom-diff`
- `POST /api/v1/eco/{eco_id}/apply`
- `GET /api/v1/eco/{eco_id}/apply-diagnostics`

The public API paths, request parameters, response shapes, auth dependencies, and `ECO` tag are preserved.

## 2. Non-Goals

- No ECO CRUD relocation.
- No cancel, suspend, unsuspend, unsuspend-diagnostics, or move-stage relocation.
- No BOM change compute/conflict relocation.
- No service-layer behavior changes.
- No schema, migration, scheduler, or shared-dev changes.

## 3. Implementation

- Added `src/yuantus/meta_engine/web/eco_impact_apply_router.py`.
- Registered `eco_impact_apply_router` in `src/yuantus/api/app.py` after `eco_approval_workflow_router` and before legacy `eco_router`.
- Removed the five moved handlers and their impact/export dependencies from `eco_router.py`.
- Retargeted focused tests that patch `ECOService` or `MetaPermissionService` for impact/apply paths.
- Added `test_eco_impact_apply_router_contracts.py` with route ownership, no legacy leakage, registration order, tag preservation, and scope boundary checks.
- Added the new router and contract test to `.github/workflows/ci.yml`.

## 4. Verification

Commands run locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/meta_engine/web/eco_impact_apply_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: `33 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

Result: `116 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `5 passed`.

```bash
git diff --check
```

Result: passed.

## 5. Review Checklist

- The moved endpoints are owned by `yuantus.meta_engine.web.eco_impact_apply_router`.
- Legacy `eco_router.py` no longer declares the moved impact/apply decorators.
- `eco_impact_apply_router` is registered before legacy `eco_router`, so parameterized legacy routes cannot shadow the moved endpoints.
- `compute-changes`, `cancel`, `suspend`, `unsuspend`, `unsuspend-diagnostics`, and `move-stage` remain outside this slice.
- Public API route paths are unchanged.
