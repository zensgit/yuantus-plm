# Quality Router Exception Chaining - Development and Verification

Date: 2026-05-13

## 1. Goal

Preserve original service exceptions when quality split routers map
`QualityService` validation failures to existing API-facing `400` responses.

This follows the same exception-chaining closeout pattern used for
document-sync, cutted-parts, and box routers. API callers keep the same status
code and detail string, while logs and debuggers retain the original
`ValueError` through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/quality_alerts_router.py`
- `src/yuantus/meta_engine/web/quality_checks_router.py`
- `src/yuantus/meta_engine/web/quality_points_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_quality_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_EXCEPTION_CHAINING_20260513.md`

## 3. Behavior

The changed paths are:

- `POST /api/v1/quality/points`
- `POST /api/v1/quality/checks`
- `POST /api/v1/quality/checks/{check_id}/record`
- `POST /api/v1/quality/alerts`
- `POST /api/v1/quality/alerts/{alert_id}/transition`

Failure responses remain:

```text
400 <original service exception text>
```

The internal raises now use:

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Existing rollback behavior is preserved for all five write paths.

## 4. Contract Coverage

The new contract verifies:

- all five quality write `400` conversion paths preserve `ValueError` as
  `HTTPException.__cause__`
- each failure path still calls `db.rollback()`
- each touched router source keeps the expected `from exc` conversion count
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `QualityService` behavior change.
- No auth dependency change.
- No transaction helper extraction.
- No quality route decomposition change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/quality_alerts_router.py \
  src/yuantus/meta_engine/web/quality_checks_router.py \
  src/yuantus/meta_engine/web/quality_points_router.py \
  src/yuantus/meta_engine/tests/test_quality_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_quality_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_quality_router_decomposition_closeout_contracts.py

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
- focused quality exception-chaining contract + decomposition contract: 12 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all five `ValueError` mapping paths use `from exc`.
- Confirm rollback behavior remains pinned for all five write paths.
- Confirm existing quality route ownership and tag contracts remain green.
