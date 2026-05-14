# Box Router Exception Chaining - Development and Verification

Date: 2026-05-13

## 1. Goal

Preserve original service exceptions when PLM Box split routers map `BoxService`
validation and lookup failures to existing API-facing `400` and `404`
responses.

This follows the same exception-chaining closeout pattern used for document-sync
and cutted-parts routers. API callers keep the same status code and detail
string, while logs and debuggers retain the original `ValueError` through
`HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/box_aging_router.py`
- `src/yuantus/meta_engine/web/box_analytics_router.py`
- `src/yuantus/meta_engine/web/box_capacity_router.py`
- `src/yuantus/meta_engine/web/box_core_router.py`
- `src/yuantus/meta_engine/web/box_custody_router.py`
- `src/yuantus/meta_engine/web/box_ops_router.py`
- `src/yuantus/meta_engine/web/box_policy_router.py`
- `src/yuantus/meta_engine/web/box_reconciliation_router.py`
- `src/yuantus/meta_engine/web/box_traceability_router.py`
- `src/yuantus/meta_engine/web/box_turnover_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_box_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_BOX_ROUTER_EXCEPTION_CHAINING_20260513.md`

## 3. Behavior

The changed paths are:

- `POST /api/v1/box/items`
- `GET /api/v1/box/items/{box_id}/export-meta`
- `GET /api/v1/box/items/{box_id}/aging`
- `GET /api/v1/box/items/{box_id}/contents-summary`
- `GET /api/v1/box/items/{box_id}/export-contents`
- `GET /api/v1/box/items/{box_id}/capacity`
- `GET /api/v1/box/items/{box_id}/custody`
- `GET /api/v1/box/items/{box_id}/ops-report`
- `GET /api/v1/box/items/{box_id}/policy-check`
- `GET /api/v1/box/items/{box_id}/reconciliation`
- `GET /api/v1/box/items/{box_id}/reservations`
- `GET /api/v1/box/items/{box_id}/turnover`

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

Existing rollback behavior is preserved for `POST /box/items`.

## 4. Contract Coverage

The new contract verifies:

- all eleven box lookup/export `404` conversion paths preserve `ValueError` as
  `HTTPException.__cause__`
- the create-box `400` conversion path preserves `ValueError` as
  `HTTPException.__cause__`
- create-box failure still calls `db.rollback()`
- each touched router source keeps the expected `from exc` conversion count
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `BoxService` behavior change.
- No auth dependency change.
- No transaction helper extraction.
- No box route decomposition change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/box_aging_router.py \
  src/yuantus/meta_engine/web/box_analytics_router.py \
  src/yuantus/meta_engine/web/box_capacity_router.py \
  src/yuantus/meta_engine/web/box_core_router.py \
  src/yuantus/meta_engine/web/box_custody_router.py \
  src/yuantus/meta_engine/web/box_ops_router.py \
  src/yuantus/meta_engine/web/box_policy_router.py \
  src/yuantus/meta_engine/web/box_reconciliation_router.py \
  src/yuantus/meta_engine/web/box_traceability_router.py \
  src/yuantus/meta_engine/web/box_turnover_router.py \
  src/yuantus/meta_engine/tests/test_box_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_box_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_box_router_decomposition_closeout_contracts.py

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
- focused box exception-chaining contract + decomposition contract: 19 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all twelve `ValueError` mapping paths use `from exc`.
- Confirm create-box rollback behavior remains pinned.
- Confirm existing box route ownership and tag contracts remain green.
