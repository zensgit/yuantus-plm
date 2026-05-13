# Approval Request Router Exception Chaining - Development and Verification

Date: 2026-05-12

## 1. Goal

Preserve original service exceptions when `approval_request_router.py` maps
approval request validation or not-found failures to existing API-facing `400`
and `404` responses.

This continues the narrow exception-chaining closeout line after app-router and
approval-ops. API callers keep the same status code and detail string, while
logs and debuggers retain the original `ValueError` through
`HTTPException.__cause__`.

## 2. Scope

Modified:

- `src/yuantus/meta_engine/web/approval_request_router.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_approval_request_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_APPROVAL_REQUEST_ROUTER_EXCEPTION_CHAINING_20260512.md`

## 3. Behavior

The four changed paths are:

- `GET /api/v1/approvals/requests/export`
- `GET /api/v1/approvals/requests/{request_id}/lifecycle`
- `GET /api/v1/approvals/requests/{request_id}/consumer-summary`
- `GET /api/v1/approvals/requests/{request_id}/history`

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

## 4. Contract Coverage

The new contract verifies:

- request export failures preserve `ValueError` as `HTTPException.__cause__`
- lifecycle not-found failures preserve `ValueError` as `HTTPException.__cause__`
- consumer-summary not-found failures preserve `ValueError` as `HTTPException.__cause__`
- history not-found failures preserve `ValueError` as `HTTPException.__cause__`
- the source keeps exactly one `400 from exc` raise and three `404 from exc`
  raises in this router
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `ApprovalService` behavior change.
- No transactional write helper change.
- No export payload contract change.
- No auth dependency change.
- No broad exception-chaining sweep across all approval routers.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/approval_request_router.py \
  src/yuantus/meta_engine/tests/test_approval_request_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_approval_request_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py

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
- focused approval-request exception-chaining contract + ownership contract: 12 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all four `ValueError` mapping paths use `from exc`.
- Confirm existing request route ownership and static/dynamic route-order
  contracts remain green.
- Confirm this is not a broad exception-chaining sweep.
