# Tail Router Exception Chaining Closeout - Development and Verification

Date: 2026-05-14

## 1. Goal

Close the remaining meta-engine web router exception-chaining gaps by preserving
original exceptions for the last bare `HTTPException(... detail=str(exc))`
conversions.

API callers keep the same status codes and detail strings. Logs and debuggers
now retain the original exception through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/router.py`
- `src/yuantus/meta_engine/web/rpc_router.py`
- `src/yuantus/meta_engine/web/product_router.py`
- `src/yuantus/meta_engine/web/bom_compare_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_tail_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_TAIL_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md`

## 3. Behavior

The changed paths are:

- `POST /api/v1/aml/apply`
- `POST /api/v1/rpc/`
- `GET /api/v1/products/{item_id}`
- `GET /api/v1/bom/compare`

Failure responses remain:

```text
400 <original exception text>
404 <original exception text>
500 <original exception text>
```

The internal raises now use:

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
raise HTTPException(status_code=404, detail=str(exc)) from exc
raise HTTPException(status_code=500, detail=str(exc)) from exc
```

Existing rollback behavior is preserved for write/dispatch paths. Read-only
product and BOM compare validation paths remain non-transactional and do not
call rollback.

## 4. Contract Coverage

The new contract verifies:

- all four tail conversion paths preserve the original exception as
  `HTTPException.__cause__`
- response status/detail semantics remain unchanged
- rollback behavior stays pinned for `aml/apply` and `rpc`
- product detail and BOM compare validation paths do not introduce rollback
  side effects
- each touched source keeps the expected `from exc` conversion
- the full `src/yuantus/meta_engine/web/*.py` directory has no remaining bare
  `detail=str(exc)` HTTPException conversions
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No service, auth, permission, or transaction helper change.
- No BOM compare behavior change beyond exception cause preservation.
- No product detail behavior change beyond exception cause preservation.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/router.py \
  src/yuantus/meta_engine/web/rpc_router.py \
  src/yuantus/meta_engine/web/product_router.py \
  src/yuantus/meta_engine/web/bom_compare_router.py \
  src/yuantus/meta_engine/tests/test_tail_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_tail_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py

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
- focused tail exception-chaining contract + adjacent router contracts:
  `21 passed`
- doc-index / CI list quartet: `5 passed`
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all four tail paths use `from exc`.
- Confirm transactional rollback behavior remains unchanged.
- Confirm the full web-router sweep has no remaining bare `detail=str(exc)`
  conversions.
