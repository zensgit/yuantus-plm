# Cutted Parts Router Exception Chaining - Development and Verification

Date: 2026-05-13

## 1. Goal

Preserve original service exceptions when cutted-parts split routers map
`CuttedPartsService` validation and lookup failures to existing API-facing
`400` and `404` responses.

This follows the same exception-chaining closeout pattern used for
document-sync routers. API callers keep the same status code and detail string,
while logs and debuggers retain the original `ValueError` through
`HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/cutted_parts_alerts_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_analytics_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_benchmark_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_core_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_scenarios_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_thresholds_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_throughput_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_utilization_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_variance_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_cutted_parts_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_CUTTED_PARTS_ROUTER_EXCEPTION_CHAINING_20260513.md`

## 3. Behavior

The changed paths are:

- `POST /api/v1/cutted-parts/plans`
- `GET /api/v1/cutted-parts/plans/{plan_id}/summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/waste-summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/cost-summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/scenarios`
- `GET /api/v1/cutted-parts/plans/{plan_id}/quote-summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/recommendations`
- `GET /api/v1/cutted-parts/plans/{plan_id}/threshold-check`
- `GET /api/v1/cutted-parts/plans/{plan_id}/alerts`
- `GET /api/v1/cutted-parts/plans/{plan_id}/cadence`
- `GET /api/v1/cutted-parts/plans/{plan_id}/bottlenecks`

Failure responses remain:

```text
400 <original service exception text>
404 <original service exception text>
```

The internal raises now use:

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
raise HTTPException(status_code=404, detail=str(exc)) from exc
```

Existing rollback behavior is preserved for `POST /cutted-parts/plans`.

## 4. Contract Coverage

The new contract verifies:

- all ten plan lookup and analytics `404` conversion paths preserve
  `ValueError` as `HTTPException.__cause__`
- the create-plan `400` conversion path preserves `ValueError` as
  `HTTPException.__cause__`
- create-plan failure still calls `db.rollback()`
- each touched router source keeps the expected `from exc` conversion count
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `CuttedPartsService` behavior change.
- No auth dependency change.
- No transaction helper extraction.
- No cutted-parts route decomposition change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cutted_parts_alerts_router.py \
  src/yuantus/meta_engine/web/cutted_parts_analytics_router.py \
  src/yuantus/meta_engine/web/cutted_parts_benchmark_router.py \
  src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py \
  src/yuantus/meta_engine/web/cutted_parts_core_router.py \
  src/yuantus/meta_engine/web/cutted_parts_scenarios_router.py \
  src/yuantus/meta_engine/web/cutted_parts_thresholds_router.py \
  src/yuantus/meta_engine/web/cutted_parts_throughput_router.py \
  src/yuantus/meta_engine/web/cutted_parts_utilization_router.py \
  src/yuantus/meta_engine/web/cutted_parts_variance_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

Results:

- `py_compile`: passed
- focused cutted-parts exception-chaining contract + decomposition contracts: 23 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all eleven `ValueError` mapping paths use `from exc`.
- Confirm create-plan rollback behavior remains pinned.
- Confirm existing cutted-parts route ownership and R1 ordering contracts remain
  green.
