# ECO Router Decomposition R2 Stage Admin - Development And Verification

Date: 2026-04-23

## 1. Goal

Continue ECO router decomposition by moving stage administration endpoints out of the large legacy `eco_router.py` into a focused router, while leaving kanban, approval writes, ECO lifecycle, apply, suspend, and impact routes untouched.

## 2. Delivered

- Added `src/yuantus/meta_engine/web/eco_stage_router.py`.
- Moved the stage DTOs and four stage administration endpoints:
  - `GET /eco/stages`
  - `POST /eco/stages`
  - `PUT /eco/stages/{stage_id}`
  - `DELETE /eco/stages/{stage_id}`
- Registered `eco_stage_router` after `eco_approval_ops_router` and before the legacy `eco_router`.
- Added `test_eco_stage_router_contracts.py` for route ownership, duplicate registration, registration order, tag preservation, and exclusion of kanban/lifecycle/approval-write routes.
- Added `test_eco_stage_router.py` for focused behavior coverage of list/create/update/delete.
- Registered the new contract test and router change-scope entry in `.github/workflows/ci.yml`.
- Updated the legacy router route-order comment to remove `/stages`.

## 3. Public API

Public URLs remain unchanged under `/api/v1/eco/stages*`. Only the internal FastAPI router owner changed.

The following routes intentionally remain outside `eco_stage_router.py`:

- `GET /eco/kanban`
- `POST /eco/{eco_id}/move-stage`
- `POST /eco/{eco_id}/auto-assign-approvers`
- `POST /eco/approvals/escalate-overdue`
- ECO CRUD, impact, apply, suspend, unsuspend, approve, reject, and approval list routes

## 4. R2 Hardening

The move exposed one narrow legacy handler issue: `delete_stage()` raised `HTTPException(404)` inside a broad `except Exception` block, which converted a missing stage into HTTP 500. R2 keeps the intended not-found contract by re-raising `HTTPException` before the catch-all rollback branch.

`StageUpdate` now uses `model_dump(exclude_unset=True)` when available, with a Pydantic v1 `dict(exclude_unset=True)` fallback. This avoids Pydantic v2 deprecation warnings without changing payload semantics.

## 5. Contract Coverage

The new contracts assert:

- all four stage routes are owned by `yuantus.meta_engine.web.eco_stage_router`;
- `create_app()` registers each moved `(method, path)` exactly once;
- legacy `eco_router.py` no longer declares `/stages` decorators;
- registration order is `eco_approval_ops_router` → `eco_stage_router` → `eco_router`;
- `ECO` tags are preserved;
- kanban, move-stage, approval auto-assign, and overdue escalation routes are not present in the stage router.

## 6. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_stage_router.py \
  src/yuantus/meta_engine/web/eco_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_p2_dev_observation_smoke.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_routing.py

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
- ECO stage router focused regression: 14 passed
- combined ECO R1/R2 + adjacent approval ops/write regression: 123 passed
- pact provider + gate: 3 passed
- doc-index + CI list contracts: 4 passed
- `git diff --check`: pass

## 7. Non-Goals

- No service-layer refactor.
- No schema, migration, permission, scheduler, UI, or shared-dev `142` changes.
- No changes to ECO lifecycle, approval writes, apply/suspend, impact export, or kanban.
- No deletion of `eco_router.py`.

## 8. Follow-Up

R3 should be another bounded ECO slice after R2 is merged and post-merge verification is green. Candidate slices are approval write routes or impact/apply diagnostics, but they should not be mixed in one PR.
