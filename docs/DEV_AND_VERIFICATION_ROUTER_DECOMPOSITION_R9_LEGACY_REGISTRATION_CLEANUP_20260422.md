# Router Decomposition R9: Legacy Registration Cleanup

Date: 2026-04-22

## 1. Goal

Remove the no-op `create_app()` registration for the empty legacy `parallel_tasks_router` after R8 moved the final `/eco-activities/*` routes into a split router.

The legacy module is intentionally retained as an import-compatible shell:

- `src/yuantus/meta_engine/web/parallel_tasks_router.py` still exports `parallel_tasks_router`.
- `parallel_tasks_router.routes` remains empty.
- Runtime app registration now uses only the dedicated split routers.

## 2. Runtime Changes

- Removed `from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router` from `src/yuantus/api/app.py`.
- Removed `app.include_router(parallel_tasks_router, prefix="/api/v1")` from `create_app()`.
- Left `parallel_tasks_router.py` in place as a compatibility import surface for older imports and route-ownership contracts.

No public API path, method, response shape, service logic, schema, authentication dependency, or transaction behavior was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_parallel_tasks_legacy_router_contracts.py`.
- Added the new legacy cleanup contract test to the CI contracts job list.

The new contract asserts:

- The legacy router remains importable and empty.
- `create_app()` no longer imports or includes the legacy router.
- Representative split router paths across R1-R8 remain registered.

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/web/parallel_tasks_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_legacy_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_*_router_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `py_compile`: passed
- Router and contract sweep: `35 passed in 4.32s`

## 5. Review Checklist

- Legacy router module remains importable.
- Legacy router is not registered in `create_app()`.
- All split router representatives remain registered.
- CI contract job explicitly includes the cleanup contract.
- Delivery doc index includes this MD entry.

## 6. Follow-Up

The router decomposition line is now functionally closed. A future breaking cleanup could delete `parallel_tasks_router.py` after confirming no external imports depend on it, but that is intentionally outside this bounded PR.
