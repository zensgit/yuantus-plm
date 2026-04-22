# Router Decomposition R7: Workflow Actions

Date: 2026-04-22

## 1. Goal

Move the `/workflow-actions/*` custom action endpoints out of the legacy `parallel_tasks_router.py` into a dedicated split router while preserving the public API surface.

This is R7 of the bounded router decomposition line:

- R1: `/doc-sync/*`
- R2: `/breakages/*`
- R3: `/parallel-ops/*`
- R4: `/cad-3d/*`
- R5: `/workorder-docs/*`
- R6: `/consumption/*`
- R7: `/workflow-actions/*`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/parallel_tasks_workflow_actions_router.py`.
- Moved the workflow action request DTOs and endpoint handlers into the new router.
- Removed `WorkflowCustomActionService` and workflow-only role helper usage from `parallel_tasks_router.py`.
- Registered `parallel_tasks_workflow_actions_router` in `src/yuantus/api/app.py` under the existing `/api/v1` prefix.

No service-layer behavior, schema, persistence, authentication dependency, route path, method, response shape, transaction boundary, role-context injection, or error contract was intentionally changed.

## 3. Route Coverage

The split router now owns 3 route contracts:

- `POST /workflow-actions/rules`
- `GET /workflow-actions/rules`
- `POST /workflow-actions/execute`

## 4. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_workflow_actions_router_contracts.py`.
- Updated `test_parallel_tasks_router.py` patch targets from `parallel_tasks_router.WorkflowCustomActionService` to `parallel_tasks_workflow_actions_router.WorkflowCustomActionService`.
- Added the new workflow actions router contract test to the CI contracts job list.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_workflow_actions_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_workflow_actions_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `py_compile`: passed
- Focused regression and contracts: `132 passed in 47.82s`

## 6. Review Checklist

- The split router owns every `/workflow-actions/*` endpoint.
- The legacy router owns no `/workflow-actions/*` endpoint after R7.
- `create_app()` registers every `/api/v1/workflow-actions/*` route exactly once.
- Existing workflow action tests still validate rule create/list and execute behavior through the public `/api/v1/workflow-actions/*` paths.
- CI contract job explicitly includes the new split router contract test.

## 7. Follow-Up

If this decomposition line continues, the legacy `parallel_tasks_router.py` now has only `/eco-activities/*`. The next bounded split should target `/eco-activities/*` as R8, after which the legacy router can be retired or turned into a compatibility import shell.
