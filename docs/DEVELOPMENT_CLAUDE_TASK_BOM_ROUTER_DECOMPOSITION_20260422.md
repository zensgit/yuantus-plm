# DEVELOPMENT Task - BOM Router Decomposition - 2026-04-22

## 1. Goal

Continue §二 architecture reduction by starting the BOM router decomposition line.

This taskbook is a planning gate before code movement. The first implementation PR must be small enough to review without revalidating the full PLM cycle, following the cadence already proven by:

- `DEVELOPMENT_CLAUDE_TASK_ROUTER_DECOMPOSITION_20260422.md` (the parent taskbook, #343)
- `parallel_tasks_router` R1–R9 (PR #344–#352)
- `cad_router` R1–R12 (PR #353–#364)

Scope: **write the BOM router decomposition taskbook and R1 route boundary only. Do not move any route code in this PR.** Implementation PRs will follow as separate bounded increments.

## 2. Current Inventory

Measured on `main` after PR #364.

`src/yuantus/meta_engine/web/bom_router.py`:

- 2146 LOC
- 29 route decorators on `@bom_router` with public prefix `/api/v1/bom`
- Functional groups share this single file

Endpoint grouping (all paths below are relative to `/api/v1/bom`, expressed as they appear in source):

| Group | # | Endpoints |
| --- | ---: | --- |
| Tree / effective / version | 4 | `GET /{item_id}/effective`, `GET /version/{version_id}`, `GET /{parent_id}/tree`, `GET /mbom/{parent_id}/tree` |
| EBOM to MBOM convert | 1 | `POST /convert/ebom-to-mbom` |
| Children add/remove | 2 | `POST /{parent_id}/children`, `DELETE /{parent_id}/children/{child_id}` |
| Obsolete | 2 | `GET /{item_id}/obsolete`, `POST /{item_id}/obsolete/resolve` |
| Rollup | 1 | `POST /{item_id}/rollup/weight` |
| Where-used | 2 | `GET /{item_id}/where-used`, `GET /where-used/schema` |
| Compare | 14 | see §4 |
| Substitutes | 3 | `GET /{bom_line_id}/substitutes`, `POST /{bom_line_id}/substitutes`, `DELETE /{bom_line_id}/substitutes/{substitute_id}` |

Application registration is centralized in `src/yuantus/api/app.py` through `app.include_router(bom_router, prefix="/api/v1")`. Endpoint compatibility must be preserved there after R1.

## 3. Recommended First Increment

Implement **R1: split the BOM compare route family out of `bom_router.py`**.

Rationale:

- The `/compare/*` surface is the largest cohesive group (14 of 29 endpoints) and has the clearest self-contained boundary.
- Its compare-specific schema and helper surface is localized (`BOMCompare*` response/schema models, `SnapshotCreateRequest`, summarized snapshot helpers, delta/export helpers). The R1 implementation must re-check exact usage before moving any model or helper.
- UOM-aware compare logic already landed (PR #334 `4e3e787`, PR #337 `f237d97`), so the slice is stable — no behavior changes are expected as part of R1.
- It avoids touching any write path (children, substitutes, obsolete-resolve) in the same PR.

R1 target files:

- new `src/yuantus/meta_engine/web/bom_compare_router.py`
- updated `src/yuantus/meta_engine/web/bom_router.py`
- updated `src/yuantus/api/app.py`
- new `src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py`
- updated existing compare route tests when their mock patch targets move from `yuantus.meta_engine.web.bom_router` to `yuantus.meta_engine.web.bom_compare_router`
- new `docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R1_COMPARE_20260422.md`
- updated `docs/DELIVERY_DOC_INDEX.md`
- updated `.github/workflows/ci.yml` (add the new contract test to the contracts job)

## 4. R1 Route Boundary

Move these 14 endpoints as-is. Path, method, request schema, response schema, status codes, permission dependency, and tag **must not change**.

| Method | Path |
| --- | --- |
| GET | `/compare/schema` |
| GET | `/compare` |
| GET | `/compare/delta/preview` |
| GET | `/compare/delta/export` |
| GET | `/compare/summarized` |
| GET | `/compare/summarized/export` |
| POST | `/compare/summarized/snapshots` |
| GET | `/compare/summarized/snapshots/compare` |
| GET | `/compare/summarized/snapshots/compare/export` |
| GET | `/compare/summarized/snapshots/{snapshot_id}/compare/current` |
| GET | `/compare/summarized/snapshots/{snapshot_id}/compare/current/export` |
| GET | `/compare/summarized/snapshots/{snapshot_id}/export` |
| GET | `/compare/summarized/snapshots/{snapshot_id}` |
| GET | `/compare/summarized/snapshots` |

The snapshot sub-family has both static paths (`/snapshots/compare`) and dynamic paths (`/snapshots/{snapshot_id}`). R1 must preserve the current declaration order: static snapshot compare routes before dynamic `{snapshot_id}` routes. This prevents `/snapshots/compare` from being captured as a snapshot id after the move.

Co-move into `bom_compare_router.py`:

- any DTO / pydantic model only used by the 14 handlers above (for example `BOMCompare*` schema models and `SnapshotCreateRequest`)
- any private helper (`_*` functions) only referenced by the 14 handlers above
- any local constants only referenced by the 14 handlers above

Do NOT co-move:

- DTOs or helpers also referenced by tree / obsolete / children / substitutes / where-used / rollup / convert handlers. Those must remain in `bom_router.py`.
- Service-layer code (`BOMService`, comparator implementations). R1 is pure route relocation, not service extraction.

## 5. Implementation Constraints (R1)

- Do not change request or response schemas.
- Do not change permission / auth dependencies.
- Do not change service calls, default query parameters, exports, or HTTP status mapping.
- Do not rename public endpoints.
- Do not collapse or rewrite comparator business logic while moving routes.
- Do not move unrelated tree / convert / children / obsolete / rollup / where-used / substitutes endpoints in R1.
- Do not add new settings, migrations, tables, or scheduler behavior.
- Do not delete `bom_router.py`. After R1 it still owns the remaining 15 endpoints.
- Do not change router tag unless reviewer explicitly asks; keep whatever tag the source currently has on each handler.

## 6. Compatibility Contract

R1 must prove route movement is behavior-preserving:

- before: `app.include_router(bom_router, prefix="/api/v1")`
- after: `app.include_router(bom_compare_router, prefix="/api/v1")` **registered before** the remaining `bom_router` (match the ordering pattern used by `cad_backend_profile_router` in PR #353)

Public URLs must be unchanged. Any external client that today calls `GET /api/v1/bom/compare?...` must continue to work without change.

Response compatibility is proven by two layers:

- route ownership contract tests in §7 (module ownership, path uniqueness, tag preservation, registration order);
- existing focused compare route regressions in §8, updated to patch `bom_compare_router` where necessary.

The route ownership contract is not expected to byte-compare every response payload by itself. Existing route tests remain the response-shape guard for the moved endpoints.

## 7. Route Ownership Contract (R1)

The new `src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py` must assert:

1. **Ownership by module**: each of the 14 paths + method pairs in §4 is served by a handler whose `__module__` resolves to `yuantus.meta_engine.web.bom_compare_router`. This prevents accidental regressions where a route silently moves back to `bom_router`.
2. **Legacy absence**: `src/yuantus/meta_engine/web/bom_router.py` must not define any handler for the 14 paths above after R1. Assert by scanning `@bom_router.(get|post)` decorators in the file.
3. **Registration order**: in `src/yuantus/api/app.py`, `bom_compare_router` is `include_router`-registered before `bom_router`.
4. **Path uniqueness**: the FastAPI app reports exactly one registered route per `(method, path)` pair for the 14 entries; no duplicates.
5. **Tag preservation**: if source handlers used a tag, the new router exposes the same tag on each moved handler.
6. **Snapshot route ordering**: static snapshot compare routes remain declared before dynamic `/{snapshot_id}` snapshot routes in `bom_compare_router.py`.

Contract test style must mirror the existing CAD R1-R12 contracts (see `src/yuantus/meta_engine/tests/test_cad_*_router_contracts.py`) so review diffs are minimal.

## 8. Focused Regression Commands (R1)

The R1 PR must run at least the following focused set locally and on CI before merge.

Compile check:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_compare_router.py \
  src/yuantus/api/app.py
```

Contract + regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Whitespace:

```bash
git diff --check
```

Pact provider (required for any route move that exposes public surface):

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

CI pact-provider wiring gate (required when `.github/workflows/ci.yml` is touched):

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

## 9. Review Checklist (R1)

| # | Check |
| --- | --- |
| 1 | All 14 compare endpoints served from `bom_compare_router.py` per contract test. |
| 2 | `bom_router.py` contains zero `@bom_router.(get|post)` decorators matching `/compare*`. |
| 3 | `app.py` registers `bom_compare_router` before `bom_router`. |
| 4 | No change in request / response schema, status code, permission dependency, or tag on any of the 14 endpoints. |
| 5 | No service-layer code modified (BOMService, comparator, baseline, plugin bom-compare). |
| 6 | No migration, no new settings, no new tables. |
| 7 | Tree / obsolete / children / substitutes / where-used / rollup / convert handlers untouched in this PR. |
| 8 | Pact provider contracts still pass. |
| 9 | Existing compare route tests are updated to patch `bom_compare_router` instead of stale `bom_router` symbols where needed. |
| 10 | Static snapshot compare routes are declared before dynamic `{snapshot_id}` routes. |
| 11 | `DELIVERY_DOC_INDEX.md` lists both the implementation `DEV_AND_VERIFICATION_*_R1_COMPARE_*` MD and this taskbook. |
| 12 | CI contracts job lists the new `test_bom_compare_router_contracts.py`. |

## 10. Explicit Non-Goals (R1)

R1 must not do these. They are later R2+ slices or outside scope entirely:

- Do not split tree / effective / version / convert / children / obsolete / rollup / where-used / substitutes routes.
- Do not extract `BOMCompareService` (service-layer split is a separate non-routing increment, register as a new taskbook).
- Do not rewrite comparator behavior (UOM-aware compare already landed in PR #334 and #337).
- Do not delete or shrink `bom_router.py` beyond removing the 14 moved handlers and their compare-only private helpers / DTOs.
- Do not change the plugin `yuantus-bom-compare` surface (no coupling with this route split).
- Do not start R2 (tree / effective) or any other BOM slice in the same PR.
- Do not touch CAD router, file router, ECO router, parallel tasks routers, or scheduler.
- Do not modify shared-dev 142 configuration or run shared-dev first-run bootstrap.
- Do not change business logic in the moved handlers even for "minor cleanup" — R1 is a mechanical route relocation.

## 11. Output Files (R1 implementation PR)

The implementation PR that executes R1 must produce:

- `src/yuantus/meta_engine/web/bom_compare_router.py` (new)
- `src/yuantus/meta_engine/web/bom_router.py` (modified: 14 handlers + compare-only helpers removed)
- `src/yuantus/api/app.py` (modified: register `bom_compare_router` before `bom_router`)
- `src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py` (new)
- existing compare route tests (modified only for import/patch targets required by the route move)
- `.github/workflows/ci.yml` (modified: contracts job includes the new contract test)
- `docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R1_COMPARE_20260422.md` (new)
- `docs/DELIVERY_DOC_INDEX.md` (modified: add the new DEV_AND_VERIFICATION MD entry)

No other file should be modified unless the reviewer explicitly requests it.

## 12. Future Slices (not part of R1)

For reference only. Each will get its own bounded increment with its own taskbook or PR:

- R2 — tree / effective / version / convert (~4-5 endpoints) split into `bom_tree_router.py`.
- R3 — children add/remove split into `bom_children_router.py`.
- R4 — obsolete + rollup split into `bom_obsolete_rollup_router.py`.
- R5 — where-used split into `bom_where_used_router.py`.
- R6 — substitutes split into `bom_substitutes_router.py`.
- (if needed) R7 — any remaining compare-adjacent handlers not covered by R1.

The exact R2+ boundaries may be adjusted once R1 lands, based on actual service-coupling observed during the relocation.

## 13. Collaboration Defaults

Per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` §8:

- Claude owns bounded implementation (this taskbook, and each R1..Rn implementation PR).
- Codex owns taskbook review, PR review, focused regression gating, shared-dev 142 readonly smoke decisions, and merge validation.
- Each R should remain small enough for independent review and rollback.

## 14. Verification of This Taskbook PR

This PR is docs-only. It produces:

- this taskbook (`docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_20260422.md`)
- a companion verification MD (`docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_TASKBOOK_20260422.md`)
- an updated `docs/DELIVERY_DOC_INDEX.md`

No runtime code is changed. Verification is limited to doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

No code, no tests, no CI workflow changes in this PR.
