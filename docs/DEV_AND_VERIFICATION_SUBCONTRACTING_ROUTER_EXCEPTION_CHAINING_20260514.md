# Subcontracting Router Exception Chaining - Development and Verification

Date: 2026-05-14

## 1. Goal

Preserve original service exceptions when subcontracting split routers map
`SubcontractingService` validation and lookup failures to existing API-facing
`400` and `404` responses.

API callers keep the same status code and detail string. Logs and debuggers now
retain the original `ValueError` through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/subcontracting_orders_router.py`
- `src/yuantus/meta_engine/web/subcontracting_analytics_router.py`
- `src/yuantus/meta_engine/web/subcontracting_approval_mapping_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_subcontracting_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_ROUTER_EXCEPTION_CHAINING_20260514.md`

## 3. Behavior

The changed paths are:

- `POST /api/v1/subcontracting/orders`
- `GET /api/v1/subcontracting/orders/{order_id}`
- `POST /api/v1/subcontracting/orders/{order_id}/assign-vendor`
- `POST /api/v1/subcontracting/orders/{order_id}/issue-material`
- `POST /api/v1/subcontracting/orders/{order_id}/record-receipt`
- `GET /api/v1/subcontracting/export/overview`
- `GET /api/v1/subcontracting/export/vendors`
- `GET /api/v1/subcontracting/export/receipts`
- `POST /api/v1/subcontracting/approval-role-mappings`
- `GET /api/v1/subcontracting/approval-role-mappings`
- `GET /api/v1/subcontracting/approval-role-mappings/export`

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

Existing rollback behavior is preserved for all write paths. Read/export paths
remain non-transactional and do not call rollback.

## 4. Contract Coverage

The new contract verifies:

- all 11 subcontracting conversion paths preserve `ValueError` as
  `HTTPException.__cause__`
- status-code semantics remain unchanged, including the order detail `404`
- write-path rollback behavior remains pinned
- read/export paths do not introduce rollback side effects
- each touched router source keeps the expected `from exc` conversion count
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `SubcontractingService` behavior change.
- No auth dependency change.
- No transaction helper extraction.
- No export payload type redesign.
- No subcontracting route decomposition change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/subcontracting_orders_router.py \
  src/yuantus/meta_engine/web/subcontracting_analytics_router.py \
  src/yuantus/meta_engine/web/subcontracting_approval_mapping_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_subcontracting_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_subcontracting_orders_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_approval_mapping_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router_decomposition_closeout_contracts.py

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
- focused subcontracting exception-chaining contract + subcontracting contracts: 36 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all 11 `ValueError` mapping paths use `from exc`.
- Confirm rollback behavior remains pinned for write paths only.
- Confirm existing subcontracting route ownership and tag contracts remain green.
