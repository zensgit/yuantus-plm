# Document Sync Analytics Router Exception Chaining - Development and Verification

Date: 2026-05-13

## 1. Goal

Preserve original service exceptions when `document_sync_analytics_router.py`
maps document-sync analytics lookup failures to existing API-facing `404`
responses.

This continues the narrow exception-chaining closeout line. API callers keep the
same status code and detail string, while logs and debuggers retain the original
`ValueError` through `HTTPException.__cause__`.

## 2. Scope

Modified:

- `src/yuantus/meta_engine/web/document_sync_analytics_router.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_document_sync_analytics_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_ANALYTICS_ROUTER_EXCEPTION_CHAINING_20260513.md`

## 3. Behavior

The two changed paths are:

- `GET /api/v1/document-sync/sites/{site_id}/analytics`
- `GET /api/v1/document-sync/jobs/{job_id}/conflicts`

Failure responses remain:

```text
404 <original service exception text>
```

The internal raises now use:

```python
raise HTTPException(status_code=404, detail=str(exc)) from exc
```

## 4. Contract Coverage

The new contract verifies:

- site analytics lookup failures preserve `ValueError` as
  `HTTPException.__cause__`
- job conflicts lookup failures preserve `ValueError` as
  `HTTPException.__cause__`
- the source keeps exactly two `404 from exc` raises in this router
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `DocumentSyncService` behavior change.
- No auth dependency change.
- No document-sync route decomposition change.
- No broad exception-chaining sweep across all document-sync routers.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/document_sync_analytics_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py

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
- focused document-sync analytics exception-chaining contract + ownership contract: 10 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm both `ValueError` mapping paths use `from exc`.
- Confirm existing document-sync analytics route ownership and
  source-declaration contracts remain green.
- Confirm this is not a broad exception-chaining sweep.
