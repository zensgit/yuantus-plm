# Router Decomposition R4: CAD 3D Overlay

Date: 2026-04-22

## 1. Goal

Move the `/cad-3d/*` 3D metadata overlay endpoints out of the legacy `parallel_tasks_router.py` into a dedicated split router while preserving the public API surface.

This is R4 of the bounded router decomposition line:

- R1: `/doc-sync/*`
- R2: `/breakages/*`
- R3: `/parallel-ops/*`
- R4: `/cad-3d/*`

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/parallel_tasks_cad_3d_router.py`.
- Moved the CAD 3D overlay request DTOs and endpoint handlers into the new router.
- Removed `ThreeDOverlayService` from `parallel_tasks_router.py`.
- Registered `parallel_tasks_cad_3d_router` in `src/yuantus/api/app.py` under the existing `/api/v1` prefix.

No service-layer behavior, schema, persistence, authentication dependency, route path, method, response shape, or error contract was intentionally changed.

## 3. Route Coverage

The split router now owns 5 route contracts:

- `POST /cad-3d/overlays`
- `GET /cad-3d/overlays/cache/stats`
- `GET /cad-3d/overlays/{document_item_id}`
- `POST /cad-3d/overlays/{document_item_id}/components/resolve-batch`
- `GET /cad-3d/overlays/{document_item_id}/components/{component_ref}`

The static cache route remains registered before the dynamic `{document_item_id}` route inside the split router.

## 4. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_cad_3d_router_contracts.py`.
- Updated `test_parallel_tasks_router.py` patch targets from `parallel_tasks_router.ThreeDOverlayService` to `parallel_tasks_cad_3d_router.ThreeDOverlayService`.
- Added the new CAD 3D router contract test to the CI contracts job list.

## 5. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/parallel_tasks_router.py \
  src/yuantus/meta_engine/web/parallel_tasks_cad_3d_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_cad_3d_router_contracts.py \
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
- Focused regression and contracts: `141 passed in 49.77s`

## 6. Review Checklist

- The split router owns every `/cad-3d/*` endpoint.
- The legacy router owns no `/cad-3d/*` endpoint after R4.
- `create_app()` registers every `/api/v1/cad-3d/*` route exactly once.
- The cache stats route remains registered before the dynamic overlay lookup route.
- Existing CAD 3D overlay tests still validate the same endpoint behavior.
- CI contract job explicitly includes the new split router contract test.

## 7. Follow-Up

If this decomposition line continues, the next bounded split should target another remaining cohesive cluster in `parallel_tasks_router.py`, such as `/workorder-docs/*`, `/consumption/*`, `/workflow-actions/*`, or `/eco-activities/*`. This R4 change deliberately does not move those clusters.
