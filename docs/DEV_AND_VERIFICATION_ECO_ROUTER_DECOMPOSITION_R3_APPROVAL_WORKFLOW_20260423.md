# ECO Router Decomposition R3 Approval Workflow - Development And Verification

Date: 2026-04-23

## 1. Goal

Continue ECO router decomposition by moving the approval workflow cluster out of the large legacy `eco_router.py` into a focused router, while keeping dashboard/audit ops, stage admin, and ECO lifecycle routes in their existing routers.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/eco_approval_workflow_router.py`.
- Moved approval workflow DTOs and ten handlers:
  - `GET /eco/approvals/pending`
  - `POST /eco/approvals/batch`
  - `GET /eco/approvals/overdue`
  - `POST /eco/approvals/notify-overdue`
  - `GET /eco/{eco_id}/approval-routing`
  - `POST /eco/{eco_id}/auto-assign-approvers`
  - `POST /eco/approvals/escalate-overdue`
  - `POST /eco/{eco_id}/approve`
  - `POST /eco/{eco_id}/reject`
  - `GET /eco/{eco_id}/approvals`
- Registered `eco_approval_workflow_router` after `eco_stage_router` and before the legacy `eco_router`.
- Added `test_eco_approval_workflow_router_contracts.py` for route ownership, duplicate registration, registration order, tag preservation, and exclusion of ops/stage/lifecycle routes.
- Added `test_eco_approval_workflow_router.py` for focused HTTP behavior of pending, batch, overdue notify, approve/reject, and approval list endpoints.
- Retargeted existing approval HTTP tests and observation smoke patches from `eco_router.ECOApprovalService` to `eco_approval_workflow_router.ECOApprovalService`.
- Registered the new contract test and router change-scope entry in `.github/workflows/ci.yml`.
- Updated the legacy router route-order comment to remove the moved approval-specific routes.

## 3. Public API

Unchanged. The moved approval workflow paths remain under `/api/v1/eco/...`; only the internal FastAPI router owner changed.

The following routes intentionally remain outside `eco_approval_workflow_router.py`:

- `GET /eco/approvals/dashboard/summary`
- `GET /eco/approvals/dashboard/items`
- `GET /eco/approvals/dashboard/export`
- `GET /eco/approvals/audit/anomalies`
- `GET|POST|PUT|DELETE /eco/stages*`
- `GET /eco/kanban`
- ECO CRUD, impact, apply, cancel, suspend, unsuspend, move-stage, change/conflict routes

## 4. Contract Coverage

The new contracts assert:

- all ten moved approval workflow routes are owned by `yuantus.meta_engine.web.eco_approval_workflow_router`;
- `create_app()` registers each moved `(method, path)` exactly once;
- legacy `eco_router.py` no longer declares the moved approval workflow decorators;
- registration order is `eco_stage_router` → `eco_approval_workflow_router` → `eco_router`;
- `ECO` tags are preserved;
- dashboard ops, stage admin, kanban, apply, and move-stage routes are not present in the workflow router.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_approval_workflow_router.py \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_routing.py \
  src/yuantus/meta_engine/tests/test_p2_dev_observation_smoke.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_routing.py \
  src/yuantus/meta_engine/tests/test_p2_dev_observation_smoke.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

git diff --check
```

Results:

- py_compile: pass
- approval workflow focused regression: 70 passed
- combined ECO R1/R2/R3 + adjacent approval regression: 138 passed
- pact provider + gate: 3 passed
- doc-index + CI list contracts: 4 passed
- `git diff --check`: pass

## 6. Non-Goals

- No service-layer refactor.
- No schema, migration, scheduler, UI, or shared-dev `142` changes.
- No changes to approval dashboard/audit ops, stage admin, ECO lifecycle, impact, apply, suspend, or move-stage behavior.
- No deletion of `eco_router.py`.

## 7. Follow-Up

R4 should be another bounded ECO slice after R3 is merged and post-merge verification is green. The safest remaining candidate is impact/apply diagnostics, but it should stay separate from ECO CRUD and suspend/unsuspend paths.
