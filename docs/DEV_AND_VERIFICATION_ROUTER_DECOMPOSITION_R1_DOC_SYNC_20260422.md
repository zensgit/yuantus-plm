# DEV / Verification - Router Decomposition R1 Doc Sync - 2026-04-22

## 1. Goal

Implement R1 from `DEVELOPMENT_CLAUDE_TASK_ROUTER_DECOMPOSITION_20260422.md`.

The change splits `/doc-sync/*` endpoints out of `parallel_tasks_router.py` into a dedicated router while preserving public API paths and behavior.

## 2. Scope

Runtime files changed:

- `src/yuantus/meta_engine/web/parallel_tasks_doc_sync_router.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/api/app.py`

Test files changed:

- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_doc_sync_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`

Docs changed:

- `docs/DEV_AND_VERIFICATION_ROUTER_DECOMPOSITION_R1_DOC_SYNC_20260422.md`
- `docs/DELIVERY_DOC_INDEX.md`

CI wiring changed:

- `.github/workflows/ci.yml`

## 3. Moved Route Set

The following routes moved from `parallel_tasks_router.py` to `parallel_tasks_doc_sync_router.py`:

| Method | Path |
| --- | --- |
| POST | `/doc-sync/sites` |
| GET | `/doc-sync/sites` |
| POST | `/doc-sync/sites/{site_id}/health` |
| POST | `/doc-sync/jobs` |
| GET | `/doc-sync/jobs` |
| GET | `/doc-sync/jobs/dead-letter` |
| POST | `/doc-sync/jobs/replay-batch` |
| GET | `/doc-sync/summary` |
| GET | `/doc-sync/summary/export` |
| GET | `/doc-sync/jobs/{job_id}` |
| POST | `/doc-sync/jobs/{job_id}/replay` |

Mounted public paths remain `/api/v1/doc-sync/*`.

## 4. Compatibility Rules

Preserved:

- HTTP methods and paths,
- request and response models,
- auth dependency,
- `DocumentMultiSiteService` calls,
- error code/status mapping,
- export streaming behavior,
- `tags=["ParallelTasks"]`.

Changed only:

- module ownership of `/doc-sync/*` endpoints,
- patch target in focused tests from `parallel_tasks_router.DocumentMultiSiteService` to `parallel_tasks_doc_sync_router.DocumentMultiSiteService`,
- explicit app registration of `parallel_tasks_doc_sync_router`.
- router test fixtures set `AUTH_MODE=optional` during TestClient execution so global auth middleware does not bypass existing dependency overrides in security-default environments.

## 5. Verification

Commands:

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_doc_sync_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py \
  -k 'doc_sync or not test_parallel_ops_router_e2e' \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_doc_sync_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_doc_sync_router_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Actual result:

- route-contract tests confirm `/api/v1/doc-sync/*` paths exist exactly once,
- old `parallel_tasks_router` no longer owns `/doc-sync/*`,
- existing parallel task tests remain green after patch-path update,
- doc-sync e2e path remains green against a real in-memory service DB,
- document index contracts remain green,
- `193 passed, 7 deselected`,
- `8 passed` for the full `test_parallel_ops_router_e2e.py`,
- `8 passed` for CI contract wiring and doc-index contracts,
- `git diff --check` and `py_compile` passed.

## 6. Acceptance

| Check | Status |
| --- | --- |
| New dedicated doc-sync router exists | Pass |
| Old router no longer has `/doc-sync` route decorators | Pass |
| App registers both split and remaining routers | Pass |
| Public paths unchanged under `/api/v1` | Pass |
| No non-doc-sync route moved | Pass |
| No service-layer rewrite | Pass |

## 7. Follow-Up

R2 can split the breakage/helpdesk cluster from `parallel_tasks_router.py`, but it should be a separate PR. Do not combine R2 with CAD/BOM/File/ECO router decomposition.
