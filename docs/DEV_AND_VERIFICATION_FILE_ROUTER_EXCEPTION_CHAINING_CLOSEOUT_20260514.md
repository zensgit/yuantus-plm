# File Router Exception Chaining Closeout - Development and Verification

Date: 2026-05-14

## 1. Goal

Close the remaining File-family router exception-chaining gaps by preserving
original exceptions for every bare `HTTPException(... detail=str(e))` mapping in
`src/yuantus/meta_engine/web/file*_router.py`.

API callers keep the same status codes and detail strings. Logs and debuggers
now retain the original exception through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/file_conversion_router.py`
- `src/yuantus/meta_engine/web/file_storage_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_file_router_exception_chaining_closeout.py`
- `docs/DEV_AND_VERIFICATION_FILE_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md`

## 3. Behavior

Changed paths cover the decomposed File surfaces:

- conversion request queueing
- conversion queue processing
- legacy `process_cad` queueing
- upload outer failure handling

Failure responses remain unchanged:

```text
500 <original exception text>
```

Existing rollback behavior is preserved. Paths that rolled back before still
roll back. This closeout only adds exception chaining.

## 4. Contract Coverage

The new contract verifies:

- representative runtime paths preserve the original exception as
  `HTTPException.__cause__`
- response status/detail semantics remain unchanged
- rollback behavior stays pinned for conversion queue and upload failures
- source-level expected `from e` conversions remain pinned
- the full `file*_router.py` family has no remaining bare stringified
  `HTTPException` mappings
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, response shape, or public API change.
- No service, auth, permission, quota, storage backend, job queue, or
  transaction helper change.
- No Phase 5, P3.4 cutover, CAD plugin, scheduler, ECO, BOM, or Version work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/meta_engine/web/file_storage_router.py \
  src/yuantus/meta_engine/tests/test_file_router_exception_chaining_closeout.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_file_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_file_router_shell_contracts.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_router_attachment_lock_guards.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

rg -n --pcre2 "raise HTTPException\\([^\\n]*detail=str\\((?:e|exc)\\)\\)(?! from )" \
  src/yuantus/meta_engine/web/file*_router.py

git diff --check
```

Results:

- `py_compile`: passed
- focused File exception-chaining + adjacent File router suites: `45 passed`
- doc-index / CI list quartet: `5 passed`
- boot check: `routes=676 middleware=4`
- File-family bare stringified exception scan: no matches
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all touched File-family paths use `from e`.
- Confirm rollback behavior remains unchanged.
- Confirm no bare `detail=str(e|exc)` mappings remain in `file*_router.py`.
- Confirm CI and doc-index entries are present and sorted.
