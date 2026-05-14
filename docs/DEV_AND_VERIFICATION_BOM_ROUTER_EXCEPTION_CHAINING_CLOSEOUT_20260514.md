# BOM Router Exception Chaining Closeout - Development and Verification

Date: 2026-05-14

## 1. Goal

Close the remaining BOM-family router exception-chaining gaps by preserving
original exceptions for every bare `HTTPException(... detail=str(e|exc))`
mapping in `src/yuantus/meta_engine/web/bom*_router.py`.

API callers keep the same status codes and detail strings. Logs and debuggers
now retain the original exception through `HTTPException.__cause__`.

## 2. Scope

Modified routers:

- `src/yuantus/meta_engine/web/bom_tree_router.py`
- `src/yuantus/meta_engine/web/bom_children_router.py`
- `src/yuantus/meta_engine/web/bom_obsolete_rollup_router.py`
- `src/yuantus/meta_engine/web/bom_substitutes_router.py`
- `src/yuantus/meta_engine/web/bom_compare_router.py`

Modified support files:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `src/yuantus/meta_engine/tests/test_bom_router_exception_chaining_closeout.py`
- `docs/DEV_AND_VERIFICATION_BOM_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md`

## 3. Behavior

Changed paths include representative failure mappings in:

- BOM tree/version/effective/MBOM tree reads
- EBOM to MBOM conversion
- BOM child add/remove writes
- obsolete BOM resolve
- substitute removal
- compare-by-version resolution

Failure responses remain unchanged:

```text
400 <original exception text>
404 <original exception text>
```

Existing rollback behavior is preserved. Write paths that rolled back before
still roll back. Read/remove paths that did not roll back before remain
unchanged.

## 4. Contract Coverage

The new contract verifies:

- representative runtime paths preserve the original exception as
  `HTTPException.__cause__`
- response status/detail semantics remain unchanged
- rollback behavior stays pinned for conversion, children, and obsolete
  resolution paths
- substitute removal remains non-transactional for this validation failure
- each touched source keeps the expected `from e` / `from exc` conversion
- the full `bom*_router.py` family has no remaining bare stringified
  `HTTPException` mappings
- CI wiring and doc-index registration stay pinned

## 5. Non-Goals

- No route path, tag, response shape, or public API change.
- No service, auth, permission, or transaction helper change.
- No BOM compare semantics change beyond exception cause preservation.
- No Phase 5, P3.4 cutover, CAD plugin, scheduler, or external-evidence work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_tree_router.py \
  src/yuantus/meta_engine/web/bom_children_router.py \
  src/yuantus/meta_engine/web/bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/web/bom_substitutes_router.py \
  src/yuantus/meta_engine/web/bom_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_router_exception_chaining_closeout.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_bom_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

rg -n --pcre2 "raise HTTPException\\([^\\n]*detail=str\\((?:e|exc)\\)\\)(?! from )" \
  src/yuantus/meta_engine/web/bom*_router.py

git diff --check
```

Results:

- `py_compile`: passed
- focused BOM exception-chaining + adjacent BOM router suites: `81 passed`
- doc-index / CI list quartet: `5 passed`
- boot check: `routes=676 middleware=4`
- BOM-family bare stringified exception scan: no matches
- `git diff --check`: clean

## 7. Review Checklist

- Confirm response status/detail remain unchanged.
- Confirm all touched BOM-family paths use `from e` / `from exc`.
- Confirm rollback behavior remains unchanged.
- Confirm no bare `detail=str(e|exc)` mappings remain in `bom*_router.py`.
- Confirm CI and doc-index entries are present and sorted.
