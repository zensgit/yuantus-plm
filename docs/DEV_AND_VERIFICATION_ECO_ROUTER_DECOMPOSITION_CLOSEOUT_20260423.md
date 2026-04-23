# ECO Router Decomposition Closeout

Date: 2026-04-23

## 1. Scope

This closeout records the final verification pass for ECO router decomposition after R1-R7.

The closeout does not move any additional runtime endpoints. It adds one global contract test that validates the complete `/api/v1/eco` route map across all split ECO routers.

## 2. Final Router Map

| Slice | Router | Route Count | Scope |
| --- | --- | ---: | --- |
| R1 | `eco_approval_ops_router.py` | 4 | Dashboard, export, and audit read surfaces |
| R2 | `eco_stage_router.py` | 4 | Stage CRUD |
| R3 | `eco_approval_workflow_router.py` | 10 | Approval workflow, routing, auto-assign, escalation |
| R4 | `eco_impact_apply_router.py` | 5 | Impact, impact export, BOM diff, apply, apply diagnostics |
| R5 | `eco_change_analysis_router.py` | 5 | Routing changes, generic changes, conflicts |
| R6 | `eco_lifecycle_router.py` | 5 | Cancel, suspend, unsuspend, move-stage |
| R7 | `eco_core_router.py` | 8 | Kanban, CRUD, bind-product, new-revision |

Total owned `/api/v1/eco` routes: 41.

`eco_router.py` remains as a compatibility shim only. It re-exports `eco_core_router` as `eco_router` and declares no route decorators.

## 3. Implementation

- Added `src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py`.
- The closeout contract asserts:
  - Every `/api/v1/eco` route has an explicit expected owner module.
  - Every `/api/v1/eco` method/path pair is registered exactly once.
  - `eco_router.py` is shim-only and has no `@eco_router.*` decorators.
  - `app.py` registers specialized routers before `eco_core_router`.
  - `/api/v1/eco-activities*` remains outside this decomposition scope.
- Added the closeout contract test to the CI contracts job.
- Registered this closeout document in `docs/DELIVERY_DOC_INDEX.md`.

## 4. Verification

Commands run locally before PR:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py
```

Result: `48 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py \
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

Result: `176 passed`.

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

- The closeout contract covers the full `/api/v1/eco` route map.
- The closeout contract excludes `/api/v1/eco-activities*` by design.
- No runtime route behavior changes are introduced.
- CI contracts job includes the closeout contract.
- Documentation index references this closeout report.

## 6. Closeout Status

Local pre-PR verification is complete. PR CI and post-merge verification are recorded in the final handoff after merge.
