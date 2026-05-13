# Approval Ops Router Exception Chaining - Development and Verification

Date: 2026-05-12

## 1. Goal

Preserve original service exceptions when `approval_ops_router.py` maps
approval operations validation failures to the existing API-facing `400`
responses.

This continues the access-guard and app-router exception-chaining closeout line:
API callers keep the same status code and detail string, while logs and
debuggers retain the original `ValueError` through `HTTPException.__cause__`.

## 2. Scope

Modified:

- `src/yuantus/meta_engine/web/approval_ops_router.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_approval_ops_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_APPROVAL_OPS_ROUTER_EXCEPTION_CHAINING_20260512.md`

## 3. Behavior

The four changed paths are:

- `GET /api/v1/approvals/summary/export`
- `GET /api/v1/approvals/ops-report/export`
- `GET /api/v1/approvals/queue-health`
- `GET /api/v1/approvals/queue-health/export`

Failure responses remain:

```text
400 <original service exception text>
```

The internal raises now use:

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
```

## 4. Contract Coverage

The new contract verifies:

- summary export failures preserve `ValueError` as `HTTPException.__cause__`
- ops report export failures preserve `ValueError` as `HTTPException.__cause__`
- queue health failures preserve `ValueError` as `HTTPException.__cause__`
- queue health export failures preserve `ValueError` as `HTTPException.__cause__`
- the source keeps exactly four `from exc` raises in this router
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `ApprovalService` behavior change.
- No export payload contract change.
- No auth dependency change.
- No broad exception-chaining sweep across all approval routers.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/approval_ops_router.py \
  src/yuantus/meta_engine/tests/test_approval_ops_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_approval_ops_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py

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
- focused approval-ops exception-chaining contract + ownership contract: 12 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

Note: the first doc-index sorting run caught the new entry before the existing
`APPROVALS_*` lines. The final index placement keeps ASCII order
(`APPROVALS` before `APPROVAL_`) and the sorting contract is green.

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all four `ValueError` mapping paths use `from exc`.
- Confirm existing route ownership contract remains green.
- Confirm this is not a broad exception-chaining sweep.
