# DEV AND VERIFICATION: BOM Router Decomposition R6 Substitutes

Date: 2026-04-23

## 1. Goal

Split the BOM substitute list/add/remove endpoints out of the legacy `bom_router.py` into a dedicated router without changing public API paths, request/response schema, auth, permission checks, lock checks, guard exception mapping, or service behavior.

## 2. Scope

Moved endpoints:

- `GET /api/v1/bom/{bom_line_id}/substitutes`
- `POST /api/v1/bom/{bom_line_id}/substitutes`
- `DELETE /api/v1/bom/{bom_line_id}/substitutes/{substitute_id}`

New owner:

- `src/yuantus/meta_engine/web/bom_substitutes_router.py`

Legacy owner after R6:

- `src/yuantus/meta_engine/web/bom_router.py` is an empty compatibility shim: it remains importable and registered after all split routers, but owns no route decorators.

## 3. Implementation

Runtime changes:

- Added `bom_substitutes_router = APIRouter(prefix="/bom", tags=["BOM"])`.
- Moved `AddSubstituteRequest`, `AddSubstituteResponse`, `RemoveSubstituteResponse`, `SubstituteEntry`, and `SubstituteListResponse`.
- Moved `list_bom_substitutes()`, `add_bom_substitute()`, and `remove_bom_substitute()` mechanically from `bom_router.py`.
- Registered routers in canonical order: `bom_compare_router -> bom_tree_router -> bom_children_router -> bom_obsolete_rollup_router -> bom_where_used_router -> bom_substitutes_router -> bom_router`.
- Left `bom_router.py` as an empty APIRouter shim so R1-R6 ownership contracts and import compatibility remain stable.
- Updated `test_latest_released_guard_router.py` patch targets from `bom_router` to `bom_substitutes_router`.
- Added `test_bom_substitutes_router_contracts.py` to CI contract checks.

Behavior intentionally preserved:

- Missing BOM line still maps to `404`.
- Invalid relationship type still maps to `400`.
- Permission denial still maps to `403`.
- Locked parent still maps to `409`.
- `NotLatestReleasedError` and `SuspendedStateError` still map to `409` with rollback.
- Add-substitute `ValueError` still maps `"not found"` / `"Invalid BOM Line"` to `404`, and other values to `400`.
- Remove-substitute `ValueError` still maps to `404`.

## 4. Tests Added

`src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py`

- Verifies all three moved routes are owned by `bom_substitutes_router`.
- Verifies moved decorators are absent from legacy `bom_router.py`.
- Verifies app registration order.
- Verifies each moved method/path is registered exactly once.
- Verifies BOM tag preservation.
- Verifies source declaration order remains list -> add -> remove.
- Verifies legacy `bom_router.py` is an empty compatibility shim.

`src/yuantus/meta_engine/tests/test_bom_substitutes_router.py`

- Covers list-substitutes 404, invalid type 400, permission 403, and success response.
- Covers add-substitute permission 403, locked parent 409, latest-released 409, suspended 409, `ValueError` mappings, and success forwarding.
- Covers remove-substitute permission 403, `ValueError` 404, and success forwarding.

## 5. Verification

Executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_substitutes_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py
```

Result: `27 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

Result: `101 passed`.

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

- Compared `HEAD:src/yuantus/meta_engine/web/bom_router.py` against the new `bom_substitutes_router.py`.
- Verified moved definitions are byte-identical after replacing `@bom_router` with `@bom_substitutes_router`.
- Verified moved definitions are absent from the legacy router.
- Verified legacy `bom_router.py` has no route decorators.

Result:

```text
ast_mechanical_move_ok=true
moved_definitions=AddSubstituteRequest,AddSubstituteResponse,RemoveSubstituteResponse,SubstituteEntry,SubstituteListResponse,add_bom_substitute,list_bom_substitutes,remove_bom_substitute
legacy_definitions_checked=0
legacy_route_decorators_present=false
```

## 6. Non-Goals

- No service-layer changes in `SubstituteService`.
- No deletion of `bom_router.py`; it remains as an empty compatibility shim.
- No schema or migration change.
- No request/response DTO shape change.
- No public route path change.
- No 142 smoke; this is a local routing decomposition with no database or deployment behavior change.

## 7. Review Checklist

- Confirm `bom_router.py` has zero `@bom_router.*` route decorators.
- Confirm `app.py` registers `bom_substitutes_router` before legacy `bom_router`.
- Confirm tests patch `yuantus.meta_engine.web.bom_substitutes_router.*`.
- Confirm `test_latest_released_guard_router.py` includes `bom_substitutes_router`.
- Confirm CI contract job includes `test_bom_substitutes_router_contracts.py` in sorted order.

## 8. Status

R6 implementation is complete locally and ready for PR review.
