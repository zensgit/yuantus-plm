# ECO Router Exception Chaining Closeout - Development and Verification

Date: 2026-05-14

## 1. Goal

Close the remaining ECO-family router exception-chaining gaps by preserving
original exceptions for every bare `HTTPException(... detail=str(e))` mapping in
`src/yuantus/meta_engine/web/eco*_router.py`.

API callers keep the same status codes and detail strings. Logs and debuggers
now retain the original exception through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/eco_approval_workflow_router.py`
- `src/yuantus/meta_engine/web/eco_change_analysis_router.py`
- `src/yuantus/meta_engine/web/eco_core_router.py`
- `src/yuantus/meta_engine/web/eco_impact_apply_router.py`
- `src/yuantus/meta_engine/web/eco_lifecycle_router.py`
- `src/yuantus/meta_engine/web/eco_stage_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_eco_router_exception_chaining_closeout.py`
- `docs/DEV_AND_VERIFICATION_ECO_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md`

## 3. Behavior

Changed paths cover the decomposed ECO surfaces:

- stage admin create/update/delete
- approval workflow auto-assign/escalate/approve/reject
- impact, export, BOM diff, apply
- routing/BOM change computation and conflict diagnostics
- lifecycle cancel/suspend/unsuspend/move-stage
- core ECO create/bind/update/delete/new-revision

Failure responses remain unchanged:

```text
400 <original exception text>
404 <original exception text>
500 <original exception text>
```

Existing transaction behavior is preserved. Paths that rolled back before still
roll back. Existing paths without rollback on a specific exception class remain
unchanged; this closeout only adds exception chaining.

## 4. Contract Coverage

The new contract verifies:

- representative runtime paths preserve the original exception as
  `HTTPException.__cause__`
- response status/detail semantics remain unchanged
- rollback behavior stays pinned for representative write paths
- source-level chained exception counts remain pinned for the six touched ECO
  router modules
- the full `eco*_router.py` family has no remaining bare stringified
  `HTTPException` mappings
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, response shape, or public API change.
- No service, auth, permission, ECO state-machine, or transaction helper change.
- No Phase 5, P3.4 cutover, CAD plugin, scheduler, file-router, BOM, or Version
  work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/eco_approval_workflow_router.py \
  src/yuantus/meta_engine/web/eco_change_analysis_router.py \
  src/yuantus/meta_engine/web/eco_core_router.py \
  src/yuantus/meta_engine/web/eco_impact_apply_router.py \
  src/yuantus/meta_engine/web/eco_lifecycle_router.py \
  src/yuantus/meta_engine/web/eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_router_exception_chaining_closeout.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_eco_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router.py \
  src/yuantus/meta_engine/tests/test_eco_core_router.py \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

rg -n --pcre2 "raise HTTPException\\([^\\n]*detail=str\\((?:e|exc)\\)\\)(?! from )" \
  src/yuantus/meta_engine/web/eco*_router.py

git diff --check
```

Results:

- `py_compile`: passed
- focused ECO exception-chaining + adjacent ECO router suites:
  `92 passed, 2 warnings`
- doc-index / CI list quartet: `5 passed`
- boot check: `routes=676 middleware=4`
- ECO-family bare stringified exception scan: no matches
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all touched ECO-family paths use `from e` / `from exc`.
- Confirm rollback behavior remains unchanged.
- Confirm no bare `detail=str(e|exc)` mappings remain in `eco*_router.py`.
- Confirm CI and doc-index entries are present and sorted.
