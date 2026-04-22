# Router Decomposition R5: Workorder Docs

Date: 2026-04-22

## 1. Goal

Move the `/workorder-docs/*` document pack endpoints out of the legacy `parallel_tasks_router.py` into a dedicated split router while preserving the public API surface.

This is R5 of the bounded router decomposition line:

- R1: `/doc-sync/*`
- R2: `/breakages/*`
- R3: `/parallel-ops/*`
- R4: `/cad-3d/*`
- R5: `/workorder-docs/*`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py`.
- Moved the workorder document link DTO, export handlers, and PDF manifest helper into the new router.
- Removed `WorkorderDocumentPackService` and the workorder-doc PDF helper from `parallel_tasks_router.py`.
- Removed `json` from the legacy router imports.
- Registered `parallel_tasks_workorder_docs_router` in `src/yuantus/api/app.py` under the existing `/api/v1` prefix.

No service-layer behavior, schema, persistence, authentication dependency, route path, method, response shape, export filename, export media type, or error contract was intentionally changed.

## 3. Route Coverage

The split router now owns 3 route contracts:

- `POST /workorder-docs/links`
- `GET /workorder-docs/links`
- `GET /workorder-docs/export`

## 4. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_workorder_docs_router_contracts.py`.
- Updated `test_parallel_tasks_router.py` patch targets from `parallel_tasks_router.WorkorderDocumentPackService` to `parallel_tasks_workorder_docs_router.WorkorderDocumentPackService`.
- Added the new workorder docs router contract test to the CI contracts job list.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_workorder_docs_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `py_compile`: passed
- Focused regression and contracts: `132 passed in 44.79s`

## 6. Review Checklist

- The split router owns every `/workorder-docs/*` endpoint.
- The legacy router owns no `/workorder-docs/*` endpoint after R5.
- `create_app()` registers every `/api/v1/workorder-docs/*` route exactly once.
- Existing workorder doc export tests still validate JSON, PDF, unsupported format, locale pass-through, and link error behavior.
- CI contract job explicitly includes the new split router contract test.

## 7. Follow-Up

If this decomposition line continues, the next bounded split should target another cohesive cluster in `parallel_tasks_router.py`: `/consumption/*`, `/workflow-actions/*`, or `/eco-activities/*`.
