# App Router Exception Chaining - Development and Verification

Date: 2026-05-12

## 1. Goal

Preserve original service exceptions when `app_router.py` maps app-framework
write failures to the existing API-facing `400` responses.

This follows the admin-auth exception-chaining fix and keeps the same behavior:
API callers still see the same status code and detail string, while logs and
debuggers retain the original exception through `HTTPException.__cause__`.

## 2. Scope

Modified:

- `src/yuantus/meta_engine/web/app_router.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_app_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_APP_ROUTER_EXCEPTION_CHAINING_20260512.md`

## 3. Behavior

The two changed paths are:

- `POST /api/v1/apps/register`
- `POST /api/v1/apps/points`

Failure responses remain:

```text
400 <original service exception text>
```

The internal raise now uses:

```python
raise HTTPException(status_code=400, detail=str(e)) from e
```

## 4. Contract Coverage

The new contract verifies:

- `register_app` failure rolls back, does not commit, preserves `RuntimeError`
  as `HTTPException.__cause__`, and keeps the same `400` detail
- `create_point` failure rolls back, does not commit, preserves `ValueError`
  as `HTTPException.__cause__`, and keeps the same `400` detail
- both success paths still commit
- the source still contains the two `from e` raises
- CI wiring and doc-index registration

## 5. Non-Goals

- No route path or request/response model change.
- No `AppService` behavior change.
- No auth dependency change.
- No broad exception-chaining sweep across all routers.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/app_router.py \
  src/yuantus/meta_engine/tests/test_app_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_app_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_app_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_router_surface_misc_execution_card.py

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
- focused app-router exception-chaining contract: 5 passed
- app-router contract + router-surface misc contract: 6 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm both failure paths use `from e`.
- Confirm success paths still commit and do not rollback.
- Confirm this is not a broad exception-chaining sweep.
