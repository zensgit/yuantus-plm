# Router Decomposition R8: ECO Activities

Date: 2026-04-22

## 1. Goal

Move the final `/eco-activities/*` endpoints out of the legacy `parallel_tasks_router.py` into a dedicated split router while preserving the public API surface.

This is R8 of the bounded router decomposition line:

- R1: `/doc-sync/*`
- R2: `/breakages/*`
- R3: `/parallel-ops/*`
- R4: `/cad-3d/*`
- R5: `/workorder-docs/*`
- R6: `/consumption/*`
- R7: `/workflow-actions/*`
- R8: `/eco-activities/*`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/parallel_tasks_eco_activities_router.py`.
- Moved the ECO activity request DTOs, datetime parsing helper, export response handling, and endpoint handlers into the new router.
- Replaced `parallel_tasks_router.py` with an empty compatibility shell that still exports `parallel_tasks_router = APIRouter(tags=["ParallelTasks"])`.
- Registered `parallel_tasks_eco_activities_router` in `src/yuantus/api/app.py` under the existing `/api/v1` prefix.

No service-layer behavior, schema, persistence, authentication dependency, route path, method, response shape, transaction boundary, SLA export behavior, or error contract was intentionally changed.

## 3. Route Coverage

The split router now owns 11 route contracts:

- `POST /eco-activities`
- `GET /eco-activities/{eco_id}`
- `POST /eco-activities/activity/{activity_id}/transition`
- `GET /eco-activities/activity/{activity_id}/transition-check`
- `POST /eco-activities/{eco_id}/transition-check/bulk`
- `POST /eco-activities/{eco_id}/transition/bulk`
- `GET /eco-activities/{eco_id}/blockers`
- `GET /eco-activities/{eco_id}/events`
- `GET /eco-activities/{eco_id}/sla`
- `GET /eco-activities/{eco_id}/sla/alerts`
- `GET /eco-activities/{eco_id}/sla/alerts/export`

## 4. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_eco_activities_router_contracts.py`.
- Updated `test_parallel_tasks_router.py` patch targets from `parallel_tasks_router.ECOActivityValidationService` to `parallel_tasks_eco_activities_router.ECOActivityValidationService`.
- Added the new ECO activities router contract test to the CI contracts job list.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_eco_activities_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_eco_activities_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `py_compile`: passed
- Focused regression and contracts: `141 passed in 48.29s`
- Full split-router contract sweep: `27 passed in 3.87s`

## 6. Review Checklist

- The split router owns every `/eco-activities/*` endpoint.
- The legacy router owns no `/eco-activities/*` endpoint after R8.
- The legacy router has no remaining business routes and only remains as a compatibility import surface.
- `create_app()` registers every `/api/v1/eco-activities/*` route exactly once.
- Existing ECO activity tests still validate create, transition, transition-check, bulk transition-check, bulk transition, SLA, SLA alerts, and SLA alerts export behavior through the public `/api/v1/eco-activities/*` paths.
- CI contract job explicitly includes the new split router contract test.

## 7. Follow-Up

The `parallel_tasks_router.py` legacy module is now an empty compatibility shell. A later cleanup can remove the no-op `app.include_router(parallel_tasks_router, prefix="/api/v1")` registration and update imports if maintainers want to fully retire the legacy module.
