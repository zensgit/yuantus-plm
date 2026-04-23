# DEV AND VERIFICATION: BOM Router Decomposition R5 Where-Used

Date: 2026-04-23

## 1. Goal

Split the BOM where-used query endpoints out of the legacy `bom_router.py` into a dedicated router without changing public API paths, request/response schema, auth, permission checks, or service behavior.

## 2. Scope

Moved endpoints:

- `GET /api/v1/bom/{item_id}/where-used`
- `GET /api/v1/bom/where-used/schema`

New owner:

- `src/yuantus/meta_engine/web/bom_where_used_router.py`

Legacy owner after R5:

- `src/yuantus/meta_engine/web/bom_router.py` retains 3 endpoints: substitutes list/add/remove.

## 3. Implementation

Runtime changes:

- Added `bom_where_used_router = APIRouter(prefix="/bom", tags=["BOM"])`.
- Moved `WhereUsedEntry`, `WhereUsedResponse`, `WhereUsedLineFieldSpec`, and `WhereUsedSchemaResponse`.
- Moved `get_where_used()` and `get_where_used_schema()` mechanically from `bom_router.py`.
- Registered routers in canonical order: `bom_compare_router -> bom_tree_router -> bom_children_router -> bom_obsolete_rollup_router -> bom_where_used_router -> bom_router`.
- Added `test_bom_where_used_router_contracts.py` to CI contract checks.

Behavior intentionally preserved:

- Missing queried item still maps to `404`.
- Item-type permission denial still maps to `403`.
- `Part BOM` relationship permission denial still maps to `403`.
- `recursive` and `max_levels` query parameters are forwarded unchanged to `BOMService.get_where_used()`.
- Missing `line` and `line_normalized` fields are still normalized to `{}`.
- Schema endpoint still returns `BOMService.line_schema()` after `Part BOM` get permission.

## 4. Tests Added

`src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py`

- Verifies both moved routes are owned by `bom_where_used_router`.
- Verifies moved decorators are absent from legacy `bom_router.py`.
- Verifies app registration order.
- Verifies each moved method/path is registered exactly once.
- Verifies BOM tag preservation.
- Verifies source declaration order remains where-used before schema.

`src/yuantus/meta_engine/tests/test_bom_where_used_router.py`

- Covers where-used 404, item permission 403, relationship permission 403, success forwarding, and response defaults.
- Covers schema endpoint 403 and success response.

## 5. Verification

Executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_where_used_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_where_used_router.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py
```

Result: `12 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

Result: `79 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

Result: `2 passed`.

Executed:

```bash
git diff --check
```

Result: clean.

Executed AST relocation audit:

- Compared `HEAD:src/yuantus/meta_engine/web/bom_router.py` against the new `bom_where_used_router.py`.
- Verified moved definitions are byte-identical after replacing `@bom_router` with `@bom_where_used_router`.
- Verified the legacy router's remaining top-level definitions are unchanged.

Result:

```text
ast_mechanical_move_ok=true
moved_definitions=WhereUsedEntry,WhereUsedLineFieldSpec,WhereUsedResponse,WhereUsedSchemaResponse,get_where_used,get_where_used_schema
legacy_definitions_checked=8
```

## 6. Non-Goals

- No service-layer changes in `BOMService`.
- No substitute route movement; substitutes remain R6.
- No schema or migration change.
- No request/response DTO shape change.
- No public route path change.
- No 142 smoke; this is a local routing decomposition with no database or deployment behavior change.

## 7. Review Checklist

- Confirm `bom_router.py` has no `/{item_id}/where-used` or `/where-used/schema` decorators.
- Confirm `app.py` registers `bom_where_used_router` before legacy `bom_router`.
- Confirm tests patch `yuantus.meta_engine.web.bom_where_used_router.*`.
- Confirm legacy substitutes definitions remain unchanged.
- Confirm CI contract job includes `test_bom_where_used_router_contracts.py` in sorted order.

## 8. Status

R5 implementation is complete locally and ready for PR review.
