# DEV AND VERIFICATION: BOM Router Decomposition Closeout

Date: 2026-04-23

## 1. Goal

Close the BOM router decomposition line after R1-R6 by proving that `bom_router.py` is now an empty compatibility shell, every moved public route is owned by its dedicated router, and the public `/api/v1/bom/*` API surface remains covered by route ownership contracts and pact provider checks.

## 2. Completed PR Chain

| Slice | PR | Router | Scope |
| --- | --- | --- | --- |
| R1 | #369 | `bom_compare_router.py` | Compare, delta, summarized compare, snapshots, exports |
| R2 | #371 | `bom_tree_router.py` | Effective BOM, version BOM, EBOM-to-MBOM convert, EBOM tree, MBOM tree |
| R3 | #372 | `bom_children_router.py` | Children add/remove |
| R4 | #373 | `bom_obsolete_rollup_router.py` | Obsolete scan, obsolete resolve, weight rollup |
| R5 | #374 | `bom_where_used_router.py` | Where-used query and where-used schema |
| R6 | #375 | `bom_substitutes_router.py` | Substitute list/add/remove |

Current `main` head at closeout:

```text
5a1eaa7 refactor: split BOM substitutes router (#375)
```

## 3. Final Router State

Registered order in `src/yuantus/api/app.py`:

```text
bom_compare_router
bom_tree_router
bom_children_router
bom_obsolete_rollup_router
bom_where_used_router
bom_substitutes_router
bom_router
```

The legacy router remains importable:

```python
from fastapi import APIRouter

bom_router = APIRouter(prefix="/bom", tags=["BOM"])
```

It owns no route decorators:

```text
grep -R "@bom_router" -n src/yuantus/meta_engine/web/bom_router.py src/yuantus/meta_engine/web/bom_*_router.py
```

Result: no matches.

Line-count snapshot:

```text
       3 src/yuantus/meta_engine/web/bom_router.py
     172 src/yuantus/meta_engine/web/bom_where_used_router.py
     203 src/yuantus/meta_engine/web/bom_children_router.py
     217 src/yuantus/meta_engine/web/bom_substitutes_router.py
     223 src/yuantus/meta_engine/web/bom_obsolete_rollup_router.py
     302 src/yuantus/meta_engine/web/bom_tree_router.py
    1106 src/yuantus/meta_engine/web/bom_compare_router.py
    2226 total
```

## 4. Verification

Executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_compare_router.py \
  src/yuantus/meta_engine/web/bom_tree_router.py \
  src/yuantus/meta_engine/web/bom_children_router.py \
  src/yuantus/meta_engine/web/bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/web/bom_where_used_router.py \
  src/yuantus/meta_engine/web/bom_substitutes_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py
```

Result: `37 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py
```

Result: `60 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Result: `1 passed, 3 warnings`.

Warnings are dependency deprecations from `relationship.models`, `websockets.legacy`, and `uvicorn` WebSocket imports. They are not introduced by this docs-only closeout.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

Result: `4 passed`.

Executed:

```bash
git diff --check
```

Result: clean.

## 5. Acceptance Criteria

- `bom_router.py` is importable and owns zero routes.
- All moved BOM route families have ownership contract tests.
- CI contract job includes all six BOM route ownership contract files.
- Split routers are registered before the empty legacy shim.
- Pact provider verification remains green.
- Doc index contracts remain green.
- No `.claude/` or `local-dev-env/` files are committed.

## 6. Non-Goals

- Do not delete `bom_router.py`; it is intentionally kept as a compatibility shim.
- Do not change public `/api/v1/bom/*` routes.
- Do not change service-layer behavior.
- Do not run shared-dev bootstrap or mutate 142.
- Do not start R7; the R1-R6 decomposition line is closed.

## 7. Status

Closeout verification is complete locally and ready for PR review.
