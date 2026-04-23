# DEV AND VERIFICATION: BOM Router Decomposition R3 Children

Date: 2026-04-23

## 1. Goal

Split the two BOM children write endpoints out of the legacy `bom_router.py` into a dedicated router without changing public API paths, request bodies, response bodies, auth, permission checks, lock checks, or service behavior.

## 2. Scope

Moved endpoints:

- `POST /api/v1/bom/{parent_id}/children`
- `DELETE /api/v1/bom/{parent_id}/children/{child_id}`

New owner:

- `src/yuantus/meta_engine/web/bom_children_router.py`

Legacy owner after R3:

- `src/yuantus/meta_engine/web/bom_router.py` retains 8 endpoints: obsolete scan/resolve, weight rollup, where-used/schema, and substitutes list/add/remove.

## 3. Implementation

Runtime changes:

- Added `bom_children_router = APIRouter(prefix="/bom", tags=["BOM"])`.
- Moved `AddChildRequest`, `AddChildResponse`, `RemoveChildResponse`, and `CycleErrorResponse`.
- Moved `add_bom_child()` and `remove_bom_child()` mechanically from `bom_router.py`.
- Registered routers in canonical order: `bom_compare_router -> bom_tree_router -> bom_children_router -> bom_router`.
- Added `test_bom_children_router_contracts.py` to CI contract checks.

Behavior intentionally preserved:

- Parent not found still maps to `404`.
- Permission denial still maps to `403`.
- Locked parent still maps to `409`.
- `CycleDetectedError` still returns `409` with the original JSON response body.
- `NotLatestReleasedError` and `SuspendedStateError` still map to `409`.
- Add-child `ValueError` still maps to `400`.
- Remove-child ambiguous UOM still maps to `400`; other `ValueError` still maps to `404`.

## 4. Tests Added

`src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py`

- Verifies both moved routes are owned by `bom_children_router`.
- Verifies moved decorators are absent from legacy `bom_router.py`.
- Verifies app registration order.
- Verifies each moved method/path is registered exactly once.
- Verifies BOM tag preservation.
- Verifies source declaration order remains add before remove.

`src/yuantus/meta_engine/tests/test_bom_children_router.py`

- Covers add-child 404, 403, locked 409, success forwarding/commit, cycle 409, latest-released 409, suspended 409, and `ValueError` 400.
- Covers remove-child 404, 403, locked 409, success UOM forwarding/commit, ambiguous UOM 400, and non-ambiguous `ValueError` 404.

## 5. Verification

Executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_children_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py
```

Result: `31 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `60 passed`.

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

- Compared `HEAD:src/yuantus/meta_engine/web/bom_router.py` against the new `bom_children_router.py`.
- Verified moved definitions are byte-identical after replacing `@bom_router` with `@bom_children_router`.
- Verified the legacy router's remaining top-level definitions are unchanged.

Result:

```text
ast_mechanical_move_ok=true
moved_definitions=AddChildRequest,AddChildResponse,CycleErrorResponse,RemoveChildResponse,add_bom_child,remove_bom_child
legacy_definitions_checked=22
```

## 6. Non-Goals

- No service-layer changes in `BOMService`.
- No obsolete/rollup/where-used/substitute route movement.
- No schema or migration change.
- No request/response DTO shape change.
- No public route path change.
- No 142 smoke; this is a local routing decomposition with no database or deployment behavior change.

## 7. Review Checklist

- Confirm `bom_router.py` has no `/{parent_id}/children` or `/{parent_id}/children/{child_id}` decorators.
- Confirm `app.py` registers `bom_children_router` before legacy `bom_router`.
- Confirm tests patch `yuantus.meta_engine.web.bom_children_router.*` for children behavior.
- Confirm legacy obsolete/rollup tests no longer carry children-specific assertions.
- Confirm CI contract job includes `test_bom_children_router_contracts.py`.

## 8. Status

R3 implementation is complete locally and ready for PR review.
