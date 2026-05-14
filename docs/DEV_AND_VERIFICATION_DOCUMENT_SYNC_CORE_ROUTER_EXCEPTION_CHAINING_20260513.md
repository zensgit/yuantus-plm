# Document Sync Core Router Exception Chaining - Development and Verification

Date: 2026-05-13

## 1. Goal

Preserve original service exceptions when `document_sync_core_router.py` maps
document-sync core write, mirror, and job-summary failures to existing
API-facing `400` and `404` responses.

This closes the remaining known document-sync router exception-chaining gap.
API callers keep the same status code and detail string, while logs and
debuggers retain the original `ValueError` through `HTTPException.__cause__`.

## 2. Scope

Modified:

- `src/yuantus/meta_engine/web/document_sync_core_router.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_document_sync_core_router_exception_chaining.py`
- `docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_CORE_ROUTER_EXCEPTION_CHAINING_20260513.md`

## 3. Behavior

The five changed paths are:

- `POST /api/v1/document-sync/sites`
- `POST /api/v1/document-sync/sites/{site_id}/mirror-probe`
- `POST /api/v1/document-sync/sites/{site_id}/mirror-execute`
- `POST /api/v1/document-sync/jobs`
- `GET /api/v1/document-sync/jobs/{job_id}/summary`

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

Existing rollback behavior is preserved for the write paths that already rolled
back on `ValueError`.

## 4. Contract Coverage

The new contract verifies:

- all four `400` conversion paths preserve `ValueError` as
  `HTTPException.__cause__`
- the `404` job summary conversion path preserves `ValueError` as
  `HTTPException.__cause__`
- write failures for create-site, mirror-execute, and create-job still call
  `db.rollback()`
- the source keeps exactly four `400 from exc` raises and one `404 from exc`
  raise in this router
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, or response shape change.
- No `DocumentSyncService` behavior change.
- No auth dependency change.
- No transaction helper extraction.
- No document-sync route decomposition change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/document_sync_core_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_exception_chaining.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_exception_chaining.py \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py

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
- focused document-sync core exception-chaining contract + ownership contract: 16 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all five `ValueError` mapping paths use `from exc`.
- Confirm rollback behavior remains pinned for the write paths that already
  rolled back.
- Confirm existing document-sync core route ownership and source-declaration
  contracts remain green.
