# Router Decomposition R6: Consumption

Date: 2026-04-22

## 1. Goal

Move the `/consumption/*` plan and template endpoints out of the legacy `parallel_tasks_router.py` into a dedicated split router while preserving the public API surface.

This is R6 of the bounded router decomposition line:

- R1: `/doc-sync/*`
- R2: `/breakages/*`
- R3: `/parallel-ops/*`
- R4: `/cad-3d/*`
- R5: `/workorder-docs/*`
- R6: `/consumption/*`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/parallel_tasks_consumption_router.py`.
- Moved the consumption request DTOs and endpoint handlers into the new router.
- Removed `ConsumptionPlanService` from `parallel_tasks_router.py`.
- Registered `parallel_tasks_consumption_router` in `src/yuantus/api/app.py` under the existing `/api/v1` prefix.

No service-layer behavior, schema, persistence, authentication dependency, route path, method, response shape, transaction boundary, or error contract was intentionally changed.

## 3. Route Coverage

The split router now owns 9 route contracts:

- `POST /consumption/plans`
- `GET /consumption/plans`
- `POST /consumption/templates/{template_key}/versions`
- `GET /consumption/templates/{template_key}/versions`
- `POST /consumption/templates/versions/{plan_id}/state`
- `POST /consumption/templates/{template_key}/impact-preview`
- `POST /consumption/plans/{plan_id}/actuals`
- `GET /consumption/plans/{plan_id}/variance`
- `GET /consumption/dashboard`

## 4. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_consumption_router_contracts.py`.
- Updated `test_parallel_tasks_router.py` patch targets from `parallel_tasks_router.ConsumptionPlanService` to `parallel_tasks_consumption_router.ConsumptionPlanService`.
- Added the new consumption router contract test to the CI contracts job list.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_consumption_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_consumption_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `py_compile`: passed
- Focused regression and contracts: `132 passed in 46.15s`

## 6. Review Checklist

- The split router owns every `/consumption/*` endpoint.
- The legacy router owns no `/consumption/*` endpoint after R6.
- `create_app()` registers every `/api/v1/consumption/*` route exactly once.
- Existing consumption tests still validate template version create, invalid create, state 404, impact preview, actual 404, and variance 404 behavior.
- CI contract job explicitly includes the new split router contract test.

## 7. Follow-Up

If this decomposition line continues, the legacy `parallel_tasks_router.py` now has only `/eco-activities/*` and `/workflow-actions/*`. The next bounded split should target `/workflow-actions/*` first because it is smaller than the ECO activity cluster.
