# Router Decomposition R3: Parallel Ops

Date: 2026-04-22

## 1. Goal

Move the `/parallel-ops/*` read/export endpoints out of the legacy `parallel_tasks_router.py` into a dedicated split router while preserving the public API surface.

This is R3 of the bounded router decomposition line:

- R1: `/doc-sync/*`
- R2: `/breakages/*`
- R3: `/parallel-ops/*`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/parallel_tasks_ops_router.py`.
- Moved the full `/parallel-ops/*` route cluster and its request DTOs into the new router.
- Removed `ParallelOpsOverviewService` and `PlainTextResponse` imports from `parallel_tasks_router.py`.
- Registered `parallel_tasks_ops_router` in `src/yuantus/api/app.py` under the existing `/api/v1` prefix.

No service-layer behavior, schema, persistence, authentication dependency, route path, method, response shape, export filename, or metric format was intentionally changed.

## 3. Route Coverage

The split router now owns 26 route contracts:

- `GET /parallel-ops/summary`
- `GET /parallel-ops/trends`
- `GET /parallel-ops/alerts`
- `GET /parallel-ops/summary/export`
- `GET /parallel-ops/trends/export`
- `GET /parallel-ops/doc-sync/failures`
- `GET /parallel-ops/workflow/failures`
- `GET /parallel-ops/breakage-helpdesk/failures`
- `GET /parallel-ops/breakage-helpdesk/failures/trends`
- `GET /parallel-ops/breakage-helpdesk/failures/triage`
- `POST /parallel-ops/breakage-helpdesk/failures/triage/apply`
- `POST /parallel-ops/breakage-helpdesk/failures/replay/enqueue`
- `GET /parallel-ops/breakage-helpdesk/failures/replay/batches`
- `GET /parallel-ops/breakage-helpdesk/failures/replay/trends`
- `GET /parallel-ops/breakage-helpdesk/failures/replay/trends/export`
- `GET /parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}`
- `GET /parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}/export`
- `POST /parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup`
- `GET /parallel-ops/breakage-helpdesk/failures/export`
- `POST /parallel-ops/breakage-helpdesk/failures/export/jobs`
- `POST /parallel-ops/breakage-helpdesk/failures/export/jobs/cleanup`
- `GET /parallel-ops/breakage-helpdesk/failures/export/jobs/overview`
- `GET /parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}`
- `POST /parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}/run`
- `GET /parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}/download`
- `GET /parallel-ops/metrics`

## 4. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_ops_router_contracts.py`.
- Updated R2 breakage router contract to remove its transitional assertion that `/parallel-ops/breakage-helpdesk/*` remained in the legacy router.
- Updated `test_parallel_tasks_router.py` patch targets from `parallel_tasks_router.ParallelOpsOverviewService` to `parallel_tasks_ops_router.ParallelOpsOverviewService`.
- Added the new ops router contract test to the CI contracts job list.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_ops_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_router_contracts.py \
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
- Focused regression and contracts: `144 passed in 56.94s`

## 6. Review Checklist

- The split router owns every `/parallel-ops/*` endpoint.
- The legacy router owns no `/parallel-ops/*` endpoint after R3.
- `create_app()` registers every `/api/v1/parallel-ops/*` route exactly once.
- Existing parallel ops router tests still validate the same endpoint behavior.
- CI contract job explicitly includes the new split router contract test.

## 7. Follow-Up

R4 should split the remaining CAD 3D overlay route cluster if the router decomposition line continues. This R3 change deliberately does not move `/cad-3d/*`, `/eco-activities/*`, `/workflow-actions/*`, `/consumption/*`, or `/workorder-docs/*`.
