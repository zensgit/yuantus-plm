# ECO Router Decomposition R1 Approval Ops - Development And Verification

Date: 2026-04-23

## 1. Goal

Split the approval operations read surface out of the large legacy `eco_router.py` without changing public URLs, response schemas, permissions, or ECO approval write behavior.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/eco_approval_ops_router.py`.
- Moved four read/export endpoints:
  - `GET /eco/approvals/dashboard/summary`
  - `GET /eco/approvals/dashboard/items`
  - `GET /eco/approvals/dashboard/export`
  - `GET /eco/approvals/audit/anomalies`
- Moved the dashboard deadline parser with those endpoints.
- Registered `eco_approval_ops_router` before the legacy `eco_router` in `create_app()`.
- Added `test_eco_approval_ops_router_contracts.py` for route ownership, duplicate registration, tag preservation, and write-path exclusion.
- Retargeted affected dashboard/audit smoke tests to patch `eco_approval_ops_router.ECOApprovalService`.
- Added missing `AUTH_MODE=optional` fixtures to ECO TestClient-only files so local router regression is not blocked by middleware-level bearer-token enforcement.
- Registered the new contract test in `.github/workflows/ci.yml` and added the new router to the contract change-scope surface.

## 3. Public API

Unchanged. The public paths remain under `/api/v1/eco/...`; only the internal FastAPI router owner changed.

The moved endpoints stay read/export only. These approval write/state-machine endpoints intentionally remain in `eco_router.py`:

- `POST /eco/{eco_id}/auto-assign-approvers`
- `POST /eco/approvals/escalate-overdue`
- `POST /eco/{eco_id}/approve`
- `POST /eco/{eco_id}/reject`
- `GET /eco/{eco_id}/approvals`

## 4. Contract Coverage

The new contract test asserts:

- all four moved routes are owned by `yuantus.meta_engine.web.eco_approval_ops_router`;
- `create_app()` registers each moved `(method, path)` exactly once;
- legacy `eco_router.py` no longer declares the moved dashboard/audit decorators;
- `eco_approval_ops_router` is registered before `eco_router`;
- `ECO` tags are preserved;
- approval write paths are not present in the new read-focused router.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_approval_ops_router.py \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_p2_dev_observation_smoke.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_routing.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py

git diff --check
```

Results:

- py_compile: pass
- ECO approval ops focused regression: 67 passed
- adjacent ECO approval write/routing regression: 42 passed
- combined ECO R1 + adjacent regression: 109 passed
- pact provider + gate: 3 passed
- doc-index + CI list contracts: 4 passed
- `git diff --check`: pass

## 6. Non-Goals

- No changes to `ECOApprovalService`.
- No changes to approval routing, auto-assign, escalation, approve, reject, or stage progression behavior.
- No public URL, response schema, auth, permission, migration, scheduler, UI, or shared-dev `142` changes.
- No deletion of `eco_router.py`.

## 7. Follow-Up

Future ECO router decomposition should be separate bounded slices. Candidate R2 boundaries are stage/admin routes or approval write routes, but only after R1 is merged and post-merge smoke is green.
