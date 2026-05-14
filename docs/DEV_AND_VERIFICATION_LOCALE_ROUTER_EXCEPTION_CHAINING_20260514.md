# Locale Router Exception Chaining - Development and Verification

Date: 2026-05-14

## 1. Goal

Preserve original service exceptions when locale router write endpoints map
`LocaleService` and `ReportLocaleService` validation failures to existing
API-facing `400` responses.

API callers keep the same status code and detail string. Logs and debuggers now
retain the original `ValueError` through `HTTPException.__cause__`.

## 2. Scope

Modified router:

- `src/yuantus/meta_engine/web/locale_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_locale_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_LOCALE_ROUTER_EXCEPTION_CHAINING_20260514.md`

## 3. Behavior

The changed paths are:

- `POST /api/v1/locale/translations`
- `POST /api/v1/locale/report-profiles`

Failure responses remain:

```text
400 <original service exception text>
```

The internal raises now use:

```python
raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Existing rollback behavior is preserved for both write paths.

## 4. Contract Coverage

The new contract verifies:

- both locale write `400` conversion paths preserve `ValueError` as
  `HTTPException.__cause__`
- each failure path still calls `db.rollback()`
- `locale_router.py` keeps exactly two `from exc` conversions for these paths
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `LocaleService` or `ReportLocaleService` behavior change.
- No auth dependency change.
- No transaction helper extraction.
- No locale route decomposition change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/locale_router.py \
  src/yuantus/meta_engine/tests/test_locale_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_locale_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_locale_router.py

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
- focused locale exception-chaining contract + locale router regression: 10 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm both `ValueError` mapping paths use `from exc`.
- Confirm rollback behavior remains pinned for both write paths.
- Confirm existing locale router behavior tests remain green.
