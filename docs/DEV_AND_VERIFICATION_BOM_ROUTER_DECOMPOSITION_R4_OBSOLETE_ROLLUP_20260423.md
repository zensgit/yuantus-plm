# DEV AND VERIFICATION: BOM Router Decomposition R4 Obsolete + Rollup

Date: 2026-04-23

## 1. Goal

Split the obsolete scan, obsolete resolve, and weight rollup BOM endpoints out of the legacy `bom_router.py` into a dedicated router without changing public API paths, request bodies, response bodies, auth, permission checks, transaction behavior, or service calls.

## 2. Scope

Moved endpoints:

- `GET /api/v1/bom/{item_id}/obsolete`
- `POST /api/v1/bom/{item_id}/obsolete/resolve`
- `POST /api/v1/bom/{item_id}/rollup/weight`

New owner:

- `src/yuantus/meta_engine/web/bom_obsolete_rollup_router.py`

Legacy owner after R4:

- `src/yuantus/meta_engine/web/bom_router.py` retains 5 endpoints: where-used/schema and substitutes list/add/remove.

## 3. Implementation

Runtime changes:

- Added `bom_obsolete_rollup_router = APIRouter(prefix="/bom", tags=["BOM"])`.
- Moved `ObsoleteScanEntry`, `ObsoleteScanResponse`, `ObsoleteResolveRequest`, `ObsoleteResolveResponse`, and `WeightRollupRequest`.
- Moved `get_obsolete_bom()`, `resolve_obsolete_bom()`, and `rollup_bom_weight()` mechanically from `bom_router.py`.
- Registered routers in canonical order: `bom_compare_router -> bom_tree_router -> bom_children_router -> bom_obsolete_rollup_router -> bom_router`.
- Added `test_bom_obsolete_rollup_router_contracts.py` to CI contract checks.

Behavior intentionally preserved:

- Missing root item still maps to `404`.
- Permission denial still maps to `403`.
- Obsolete resolve `ValueError` still maps to `400` with rollback.
- Obsolete resolve dry-run still rolls back instead of committing.
- Weight rollup write-back still requires update permission and commits only when `write_back=true`.
- Query/body parameter forwarding to `BOMObsoleteService` and `BOMRollupService` is unchanged.

## 4. Tests Added

`src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py`

- Verifies all three moved routes are owned by `bom_obsolete_rollup_router`.
- Verifies moved decorators are absent from legacy `bom_router.py`.
- Verifies app registration order.
- Verifies each moved method/path is registered exactly once.
- Verifies BOM tag preservation.
- Verifies source declaration order remains obsolete scan -> obsolete resolve -> rollup weight.

`src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py`

- Updated the isolated FastAPI app to include `bom_obsolete_rollup_router`.
- Updated service/permission patch targets to the new module.
- Added coverage for relationship type forwarding, dry-run rollback, and write-back commit.

## 5. Verification

Executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_obsolete_rollup_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py
```

Result: `12 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_children_router.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

Result: `67 passed`.

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

Executed:

```bash
npx playwright test playwright/tests/bom_obsolete_weight.spec.js --workers=1
```

Result: `2 passed`.

Executed AST relocation audit:

- Compared `HEAD:src/yuantus/meta_engine/web/bom_router.py` against the new `bom_obsolete_rollup_router.py`.
- Verified moved definitions are byte-identical after replacing `@bom_router` with `@bom_obsolete_rollup_router`.
- Verified the legacy router's remaining top-level definitions are unchanged.

Result:

```text
ast_mechanical_move_ok=true
moved_definitions=ObsoleteResolveRequest,ObsoleteResolveResponse,ObsoleteScanEntry,ObsoleteScanResponse,WeightRollupRequest,get_obsolete_bom,resolve_obsolete_bom,rollup_bom_weight
legacy_definitions_checked=14
```

## 6. Non-Goals

- No service-layer changes in `BOMObsoleteService` or `BOMRollupService`.
- No where-used or substitute route movement.
- No schema or migration change.
- No request/response DTO shape change.
- No public route path change.
- No 142 smoke; this is a local routing decomposition with no database or deployment behavior change.

## 7. Review Checklist

- Confirm `bom_router.py` has no `/{item_id}/obsolete`, `/{item_id}/obsolete/resolve`, or `/{item_id}/rollup/weight` decorators.
- Confirm `app.py` registers `bom_obsolete_rollup_router` before legacy `bom_router`.
- Confirm tests patch `yuantus.meta_engine.web.bom_obsolete_rollup_router.*` for R4 behavior.
- Confirm legacy where-used and substitutes definitions remain unchanged.
- Confirm CI contract job includes `test_bom_obsolete_rollup_router_contracts.py` in sorted order.

## 8. Status

R4 implementation is complete locally and ready for PR review.
