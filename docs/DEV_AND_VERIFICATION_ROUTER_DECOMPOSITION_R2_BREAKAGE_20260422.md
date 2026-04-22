# DEV / Verification - Router Decomposition R2 Breakage - 2026-04-22

## 1. Goal

Implement R2 from `DEVELOPMENT_CLAUDE_TASK_ROUTER_DECOMPOSITION_20260422.md`.

The change splits the top-level `/breakages*` endpoints out of `parallel_tasks_router.py` into a dedicated router while preserving public API paths and behavior.

## 2. Scope

Runtime files changed:

- `src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/api/app.py`

Test files changed:

- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_router_contracts.py`

CI wiring changed:

- `.github/workflows/ci.yml`

Docs changed:

- `docs/DEV_AND_VERIFICATION_ROUTER_DECOMPOSITION_R2_BREAKAGE_20260422.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Moved Route Set

The following routes moved from `parallel_tasks_router.py` to `parallel_tasks_breakage_router.py`:

| Method | Path |
| --- | --- |
| GET | `/breakages/metrics` |
| GET | `/breakages/metrics/groups` |
| GET | `/breakages/metrics/export` |
| GET | `/breakages/metrics/groups/export` |
| POST | `/breakages` |
| GET | `/breakages` |
| GET | `/breakages/export` |
| GET | `/breakages/cockpit` |
| GET | `/breakages/cockpit/export` |
| POST | `/breakages/export/jobs` |
| POST | `/breakages/export/jobs/cleanup` |
| GET | `/breakages/export/jobs/{job_id}` |
| GET | `/breakages/export/jobs/{job_id}/download` |
| POST | `/breakages/{incident_id}/status` |
| POST | `/breakages/{incident_id}/helpdesk-sync` |
| GET | `/breakages/{incident_id}/helpdesk-sync/status` |
| POST | `/breakages/{incident_id}/helpdesk-sync/execute` |
| POST | `/breakages/{incident_id}/helpdesk-sync/result` |
| POST | `/breakages/{incident_id}/helpdesk-sync/ticket-update` |

Mounted public paths remain `/api/v1/breakages*`.

## 4. Compatibility Rules

Preserved:

- HTTP methods and paths,
- request and response models,
- auth dependency,
- `BreakageIncidentService` calls,
- error code/status mapping,
- export streaming behavior,
- `tags=["ParallelTasks"]`.

Intentionally not moved:

- `/parallel-ops/breakage-helpdesk/*` endpoints remain in `parallel_tasks_router.py`.
- `ParallelOpsBreakageHelpdesk*` request models remain in `parallel_tasks_router.py`.

Changed only:

- module ownership of top-level `/breakages*` endpoints,
- patch target in focused tests from `parallel_tasks_router.BreakageIncidentService` to `parallel_tasks_breakage_router.BreakageIncidentService`,
- explicit app registration of `parallel_tasks_breakage_router`,
- CI contracts list now includes the new route ownership contract test.

## 5. Verification

Commands:

```bash
git diff --check

.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Actual result:

- `141 passed`,
- `9 passed` for CI wiring, doc-index, and breakage route ownership contracts after documenting results,
- `git diff --check` passed,
- `py_compile` passed.

## 6. Acceptance

| Check | Status |
| --- | --- |
| New dedicated breakage router exists | Pass |
| Old router no longer has top-level `/breakages` route decorators | Pass |
| `/parallel-ops/breakage-helpdesk/*` remains in old router | Pass |
| App registers split and remaining routers explicitly | Pass |
| Public paths unchanged under `/api/v1` | Pass |
| No service-layer rewrite | Pass |

## 7. Follow-Up

R3 can split the `/parallel-ops/*` read/export cluster, including `/parallel-ops/breakage-helpdesk/*`, but it should be a separate PR. Do not combine R3 with CAD/BOM/File/ECO router decomposition.
