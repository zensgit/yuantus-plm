# DEVELOPMENT Task - BOM Router Decomposition R2 - 2026-04-22

## 1. Goal

Continue §二 BOM router decomposition with a bounded R2 slice after R1 landed cleanly (PR #369 merge `f271102`).

R2 moves the structure-reading and conversion route family out of `bom_router.py` into a new `bom_tree_router.py`. Scope is locked to **tree / effective / version / convert** — 5 endpoints — and must **not** expand into children add/remove, obsolete scan/resolve, rollup, where-used, or substitutes.

Precedent:

- Parent taskbook: `docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_20260422.md` (PR #368)
- R1 (compare, 14 endpoints) landed via PR #369 / merge `f271102`.
- Reference implementation cadence: CAD R1–R12 (PR #353–#364) and BOM R1 (PR #369).

Scope: **write code**. This R2 implementation PR moves route code, updates app registration, adds route-ownership contract tests, updates existing tests whose `patch(...)` targets move, updates the CI contracts job, and produces a DEV_AND_VERIFICATION MD plus index entry. It is not a planning-only PR.

## 2. Current Inventory (post-R1)

Measured on `main` at `f271102`.

`src/yuantus/meta_engine/web/bom_router.py`:

- 1062 LOC
- 15 route decorators on `@bom_router` with public prefix `/api/v1/bom`

Endpoint grouping (all paths below are relative to `/api/v1/bom`):

| Group | # | Endpoints |
| --- | ---: | --- |
| Tree / effective / version | 4 | `GET /{item_id}/effective`, `GET /version/{version_id}`, `GET /{parent_id}/tree`, `GET /mbom/{parent_id}/tree` |
| EBOM to MBOM convert | 1 | `POST /convert/ebom-to-mbom` |
| Children add/remove | 2 | `POST /{parent_id}/children`, `DELETE /{parent_id}/children/{child_id}` |
| Obsolete | 2 | `GET /{item_id}/obsolete`, `POST /{item_id}/obsolete/resolve` |
| Rollup | 1 | `POST /{item_id}/rollup/weight` |
| Where-used | 2 | `GET /{item_id}/where-used`, `GET /where-used/schema` |
| Substitutes | 3 | `GET /{bom_line_id}/substitutes`, `POST /{bom_line_id}/substitutes`, `DELETE /{bom_line_id}/substitutes/{substitute_id}` |

Total 15; R2 takes 5 (tree + effective + version + convert); bom_router.py retains 10 after R2.

## 3. Recommended Increment

Implement **R2: split tree / effective / version / convert routes out of `bom_router.py`** into a new `bom_tree_router.py`.

Rationale:

- These 5 endpoints are the cohesive "BOM structure read + EBOM→MBOM conversion" family.
- They share a helper (`_parse_config_selection`) that is used **only** by these 3 out of 5 endpoints (effective / tree / mbom tree), verified by grep over post-R1 `bom_router.py`.
- They do not share DTOs with children / obsolete / rollup / where-used / substitutes.
- Post-R1 `bom_router.py` still imports `CycleDetectedError` from `BOMService`; that is raised only by the children-add handler (outside R2). R2 must not touch that import.
- EBOM→MBOM convert is the natural neighbor of tree reading (same service `BOMConversionService`, both operate on structure trees).

R2 target files:

- new `src/yuantus/meta_engine/web/bom_tree_router.py`
- updated `src/yuantus/meta_engine/web/bom_router.py`
- updated `src/yuantus/api/app.py`
- new `src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py`
- new `src/yuantus/meta_engine/tests/test_bom_tree_router.py` with direct route behavior regressions for the 5 moved endpoints
- updated existing tree / effective / convert route tests when their `patch(...)` targets move from `yuantus.meta_engine.web.bom_router` to `yuantus.meta_engine.web.bom_tree_router`
- new `docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R2_TREE_20260422.md`
- updated `docs/DELIVERY_DOC_INDEX.md`
- updated `.github/workflows/ci.yml` (add the new contract test to the contracts job)

## 4. R2 Route Boundary

Move these 5 endpoints as-is. Path, method, request schema, response schema, status codes, permission dependency, and tag **must not change**.

| Method | Path |
| --- | --- |
| GET | `/{item_id}/effective` |
| GET | `/version/{version_id}` |
| POST | `/convert/ebom-to-mbom` |
| GET | `/{parent_id}/tree` |
| GET | `/mbom/{parent_id}/tree` |

Preserve source declaration order in the new file as a mechanical relocation guard. The current source order is: `/{item_id}/effective` at L168 before `/version/{version_id}` at L225 before `/convert/ebom-to-mbom` at L247 before `/{parent_id}/tree` at L306 before `/mbom/{parent_id}/tree` at L366. These routes do not currently collide by path shape, but R2 must keep this order so reviewers can compare the move mechanically.

**Co-move into `bom_tree_router.py`:**

- DTOs only used by the 5 handlers above:
  - `ConvertBomRequest` (post-R1 bom_router.py L88)
  - `ConvertBomResponse` (post-R1 bom_router.py L94)
- Helper `_parse_config_selection` (post-R1 bom_router.py L31) — all 3 of its callers are R2 handlers.
- Service imports used only by R2 handlers:
  - `BOMConversionService` (only `convert_ebom_to_mbom` uses it).
- Any module-level constants only referenced by the 5 handlers above (none identified pre-move; re-check during implementation).

**Do NOT co-move:**

- `_parse_config_selection` is R2-only only if the grep reconfirms at implementation time; re-run `grep -n _parse_config_selection src/yuantus/meta_engine/web/bom_router.py` before deletion and abort if any non-R2 caller appears.
- `CycleDetectedError` import or handling — stays in `bom_router.py` (raised by children-add handler outside R2).
- `is_item_locked` — used by substitutes and children handlers too, stays in `bom_router.py`. R2 handlers currently don't call it, so no cross-move concern.
- Any DTO also referenced by children / obsolete / rollup / where-used / substitutes handlers. Those must remain in `bom_router.py`.
- Service-layer code (`BOMService`, `BOMConversionService` implementations). R2 is pure route relocation, not service extraction.
- The `fastapi.responses.JSONResponse` import — bom_router.py still uses it for children DELETE (outside R2). R2 doesn't use it either; do not add it to the new router unless a moved handler requires it.

## 5. Implementation Constraints (R2)

- Do not change request or response schemas.
- Do not change permission / auth dependencies.
- Do not change service calls, default query parameters, exports, or HTTP status mapping.
- Do not rename public endpoints.
- Do not collapse or rewrite tree explosion, effectivity filtering, version resolution, or EBOM→MBOM conversion business logic while moving routes.
- Do not move unrelated children / obsolete / rollup / where-used / substitutes endpoints in R2.
- Do not add new settings, migrations, tables, or scheduler behavior.
- Do not delete `bom_router.py`. After R2 it still owns the remaining 10 endpoints.
- Do not change router tag unless reviewer explicitly asks; keep `tags=["BOM"]` on each moved handler.
- Do not touch the compare router or any compare test file. R1 is sealed.

## 6. Compatibility Contract

R2 must prove route movement is behavior-preserving.

Registration:

- before: `app.include_router(bom_compare_router, prefix="/api/v1")` then `app.include_router(bom_router, prefix="/api/v1")`
- after: `app.include_router(bom_compare_router, prefix="/api/v1")` then `app.include_router(bom_tree_router, prefix="/api/v1")` then `app.include_router(bom_router, prefix="/api/v1")`

`bom_tree_router` must be registered **before** `bom_router` so that any route resolution that prefers the first-declared router keeps the same module-resolution behavior as today.

Public URLs must be unchanged. Any external client that today calls `GET /api/v1/bom/{item_id}/effective?...`, `GET /api/v1/bom/version/{version_id}`, `POST /api/v1/bom/convert/ebom-to-mbom`, `GET /api/v1/bom/{parent_id}/tree`, or `GET /api/v1/bom/mbom/{parent_id}/tree` must continue to work without change.

Response compatibility is proven by two layers:

- route ownership contract tests in §7 (module ownership, path uniqueness, tag preservation, registration order);
- existing focused tree / convert / version route regressions in §8, updated to patch `bom_tree_router` where necessary.

## 7. Route Ownership Contract (R2)

The new `src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py` must assert:

1. **Ownership by module**: each of the 5 paths + method pairs in §4 is served by a handler whose `__module__` resolves to `yuantus.meta_engine.web.bom_tree_router`.
2. **Legacy absence**: `src/yuantus/meta_engine/web/bom_router.py` must not define any handler for the 5 paths above after R2. Assert by scanning `@bom_router.(get|post|delete|put|patch)` decorators in the file.
3. **Registration order**: in `src/yuantus/api/app.py`, `bom_tree_router` is `include_router`-registered after `bom_compare_router` and before `bom_router`.
4. **Path uniqueness**: the FastAPI app reports exactly one registered route per `(method, path)` pair for the 5 entries; no duplicates.
5. **Tag preservation**: each moved handler still exposes the `BOM` tag.
6. **Source declaration order** in `bom_tree_router.py`: the literal for `/{item_id}/effective` appears before `/version/{version_id}`, before `/convert/ebom-to-mbom`, before `/{parent_id}/tree`, before `/mbom/{parent_id}/tree`. This is a mechanical relocation guard matching post-R1 `bom_router.py` source order.

Contract test style must mirror `test_bom_compare_router_contracts.py` (R1) so reviewer diffs are minimal.

The R2 implementation must also add `src/yuantus/meta_engine/tests/test_bom_tree_router.py` because current main does not have direct route-level tests named `test_bom_tree_effectivity_router.py` or `test_bom_ebom_to_mbom_router.py`. The new behavior regression file must cover at minimum:

- `GET /api/v1/bom/{item_id}/effective` forwards effectivity/config parameters and maps missing item / permission denial;
- `GET /api/v1/bom/version/{version_id}` calls `BOMService.get_bom_for_version` and maps `ValueError` to 404;
- `POST /api/v1/bom/convert/ebom-to-mbom` checks root item type, permissions, rollback on `ValueError`, and returns `ConvertBomResponse`;
- `GET /api/v1/bom/{parent_id}/tree` forwards depth/effectivity/config parameters and maps invalid config JSON to 400;
- `GET /api/v1/bom/mbom/{parent_id}/tree` enforces `Manufacturing Part`, uses `relationship_types=["Manufacturing BOM"]`, and maps not-found / permission denial.

Use the same router-unit style as `test_bom_obsolete_rollup_router.py`; if middleware auth blocks dependency overrides, add the `AUTH_MODE=optional` autouse fixture pattern used by PR #340 and BOM R1.

## 8. Focused Regression Commands (R2)

The R2 PR must run at least the following focused set locally and on CI before merge.

Compile check:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_tree_router.py \
  src/yuantus/api/app.py
```

Contract + regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

At implementation time:

- Run `rg -n "yuantus\.meta_engine\.web\.bom_router\.(get_effective_bom|get_bom_by_version|convert_ebom_to_mbom|get_bom_tree|get_mbom_tree|_parse_config_selection)" src/` and add every hit to the focused set. Re-point their patch targets to `bom_tree_router` where needed.
- If any of those tests overrides `get_current_user` via `app.dependency_overrides` but relies on global auth middleware passing, add the same `AUTH_MODE=optional` autouse fixture pattern that PR #340 and BOM R1 used.

Whitespace:

```bash
git diff --check
```

Pact provider (required because R2 moves public routes that appear in the OpenAPI surface):

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

## 9. Review Checklist (R2)

| # | Check |
| --- | --- |
| 1 | All 5 tree / effective / version / convert endpoints served from `bom_tree_router.py` per contract test. |
| 2 | `bom_router.py` contains zero `@bom_router.(get|post|delete|put|patch)` decorators matching `/{item_id}/effective`, `/version/{version_id}`, `/convert/ebom-to-mbom`, `/{parent_id}/tree`, `/mbom/{parent_id}/tree`. |
| 3 | `app.py` registers `bom_tree_router` after `bom_compare_router` and before `bom_router`. |
| 4 | No change in request / response schema, status code, permission dependency, or tag on any of the 5 endpoints. |
| 5 | No service-layer code modified (BOMService, BOMConversionService). |
| 6 | No migration, no new settings, no new tables. |
| 7 | Children / obsolete / rollup / where-used / substitutes handlers untouched in this PR. |
| 8 | Compare router untouched in this PR (R1 seal). |
| 9 | Pact provider real verifier and CI wiring gate pass. |
| 10 | `DELIVERY_DOC_INDEX.md` lists both the implementation `DEV_AND_VERIFICATION_*_R2_TREE_*` MD and this taskbook companion. |
| 11 | CI contracts job lists the new `test_bom_tree_router_contracts.py`. |
| 12 | `_parse_config_selection` was re-grepped pre-move; all callers confirmed to be R2 handlers before deletion from `bom_router.py`. |
| 13 | Source declaration order in `bom_tree_router.py` matches §4 (effective → version → convert → tree → mbom tree). |
| 14 | New `test_bom_tree_router.py` covers all 5 moved endpoints at route behavior level. |

## 10. Explicit Non-Goals (R2)

R2 must not do these. They are later R3+ slices or outside scope entirely:

- Do not split children add/remove, obsolete scan/resolve, rollup, where-used, or substitutes routes.
- Do not extract `BOMConversionService` internals (service-layer split is a separate non-routing increment and would need its own taskbook).
- Do not rewrite tree explosion, effectivity filtering, or conversion semantics.
- Do not delete `bom_router.py`.
- Do not touch the compare router, its tests, or its CI entry.
- Do not touch plugin `yuantus-bom-compare` or any BOM plugin.
- Do not start R3 or any other BOM slice in the same PR.
- Do not touch CAD router, file router, ECO router, parallel tasks routers, or scheduler.
- Do not modify shared-dev 142 configuration or run shared-dev first-run bootstrap.
- Do not change business logic in the moved handlers even for "minor cleanup" — R2 is a mechanical route relocation.

## 11. Output Files (R2 implementation PR)

The implementation PR that executes R2 must produce:

- `src/yuantus/meta_engine/web/bom_tree_router.py` (new)
- `src/yuantus/meta_engine/web/bom_router.py` (modified: 5 handlers + ConvertBomRequest/Response + `_parse_config_selection` + `BOMConversionService` import removed; remove any now-dead import that was only used by R2)
- `src/yuantus/api/app.py` (modified: register `bom_tree_router` between `bom_compare_router` and `bom_router`)
- `src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py` (new)
- `src/yuantus/meta_engine/tests/test_bom_tree_router.py` (new direct route behavior tests for the 5 moved endpoints)
- `.github/workflows/ci.yml` (modified: contracts job includes the new contract test)
- `docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R2_TREE_20260422.md` (new)
- `docs/DELIVERY_DOC_INDEX.md` (modified: add the new DEV_AND_VERIFICATION MD entry)

Updates allowed (non-new) when patch targets move:

- any existing test file that patches a tree / convert / effective function on `yuantus.meta_engine.web.bom_router`, repointed to `yuantus.meta_engine.web.bom_tree_router`
- same files: add `AUTH_MODE=optional` autouse fixture if they return `401` pre-R2 due to middleware-vs-override ordering (PR #340 precedent)

No other file should be modified unless the reviewer explicitly requests it.

## 12. Future Slices (not part of R2)

For reference only. Each becomes its own bounded increment with its own taskbook or PR:

- R3 — children add/remove split into `bom_children_router.py` (2 endpoints).
- R4 — obsolete scan + obsolete resolve + rollup weight split into `bom_obsolete_rollup_router.py` (3 endpoints).
- R5 — where-used + where-used schema split into `bom_where_used_router.py` (2 endpoints).
- R6 — substitutes list/add/remove split into `bom_substitutes_router.py` (3 endpoints).

Actual boundaries for R3+ will be re-confirmed once R2 lands and exposes any previously hidden helper coupling.

## 13. Collaboration Defaults

Per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` §8:

- Claude owns bounded implementation (this taskbook + the R2 implementation PR).
- Codex owns taskbook review, PR review, focused regression gating, shared-dev 142 readonly smoke decisions, and merge validation.
- Each R should remain small enough for independent review and rollback.

## 14. Verification of This Taskbook PR

This taskbook PR is docs-only. It produces:

- this taskbook (`docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_R2_20260422.md`)
- a companion verification MD (`docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R2_TASKBOOK_20260422.md`)
- an updated `docs/DELIVERY_DOC_INDEX.md`

No runtime code is changed. No test is added or modified. No CI workflow is changed. Verification is limited to doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: 3 passed.
