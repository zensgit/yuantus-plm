# DEV / Verification - BOM Router Decomposition R2 Taskbook - 2026-04-22

## 1. Goal

Record the planning gate for R2 of the BOM router decomposition, produced under `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` P1 slot, after R1 (compare, 14 endpoints) landed cleanly at `f271102`.

This companion MD covers the taskbook-writing PR only. It does not move route code and does not create the R2 implementation PR.

## 2. What This PR Delivers

- `docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_R2_20260422.md` — the R2 taskbook.
- `docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R2_TASKBOOK_20260422.md` — this file.
- `docs/DELIVERY_DOC_INDEX.md` — two new entries under the Development & Verification section.

## 3. What This PR Does NOT Deliver

- No change to `src/yuantus/meta_engine/web/bom_router.py`.
- No new file `bom_tree_router.py`.
- No change to `src/yuantus/api/app.py`.
- No new or modified tests other than doc-index contracts.
- No change to `.github/workflows/ci.yml`.
- No change to `bom_compare_router.py` or any compare test (R1 seal preserved).
- No change to any BOM service-layer code.
- No CAD / file / ECO / parallel-tasks / scheduler router changes.
- No shared-dev 142 interaction.

## 4. Decisions Encoded In The Taskbook

### 4.1 R2 Slice = Tree / Effective / Version / Convert (5 endpoints)

The taskbook locks R2 to the 5 endpoints rooted at:

- `GET /api/v1/bom/{item_id}/effective`
- `GET /api/v1/bom/version/{version_id}`
- `POST /api/v1/bom/convert/ebom-to-mbom`
- `GET /api/v1/bom/{parent_id}/tree`
- `GET /api/v1/bom/mbom/{parent_id}/tree`

Rationale:

- All 5 belong to the "BOM structure read + EBOM→MBOM conversion" family.
- `_parse_config_selection` helper (post-R1 `bom_router.py` L31) is used by **only** 3 handlers, all within this R2 set. The grep check is documented as a pre-move guard in taskbook §8 and §9.
- The group does not share DTOs with the remaining 10 endpoints (children / obsolete / rollup / where-used / substitutes).

### 4.2 R2 Target File Name

`src/yuantus/meta_engine/web/bom_tree_router.py`, matching the parent taskbook #368 §12 sketch and the BOM R1 pattern (`bom_compare_router.py`).

### 4.3 Forbidden Work

Taskbook §5 / §9 / §10 explicitly forbid modifying:

- `BOMService` / `BOMConversionService` internals (service-layer unchanged);
- `bom_compare_router.py` or any compare-owned helper / test (R1 seal);
- request / response schema;
- permission / tag / HTTP status;
- helpers or DTOs used by non-R2 handlers.

The reason is to keep the R2 diff mechanical and independently rollback-able.

### 4.4 Route Ownership Contract Required

Taskbook §7 requires a dedicated `test_bom_tree_router_contracts.py` that asserts:

- module ownership per moved path,
- legacy absence in `bom_router.py`,
- registration order in `app.py` (`bom_compare_router` → `bom_tree_router` → `bom_router`),
- path uniqueness in the FastAPI app,
- `BOM` tag preservation,
- source declaration order: `/{item_id}/effective` → `/version/{version_id}` → `/convert/ebom-to-mbom` → `/{parent_id}/tree` → `/mbom/{parent_id}/tree`.

Contract style must mirror the BOM R1 contract and the CAD R1–R12 contracts so reviewer diffs are minimal.

### 4.5 Direct Route Behavior Tests Required

Codex review found that current main has no direct route-level test files named `test_bom_tree_effectivity_router.py` or `test_bom_ebom_to_mbom_router.py`. The R2 taskbook was patched to require a new `src/yuantus/meta_engine/tests/test_bom_tree_router.py` file.

That file must cover all 5 moved endpoints at behavior level, not just route ownership:

- effective BOM route parameter forwarding, missing item, permission denial;
- version BOM route service call and `ValueError` to 404 mapping;
- EBOM→MBOM conversion success, invalid root, permission denial, rollback on `ValueError`;
- tree route depth/effectivity/config forwarding and invalid config JSON;
- MBOM tree route Manufacturing Part validation and `relationship_types=["Manufacturing BOM"]`.

### 4.6 Pre-Move Guard On `_parse_config_selection`

Taskbook §4 and §9 require the implementation PR to re-run:

```bash
rg -n "_parse_config_selection" src/yuantus/meta_engine/web/bom_router.py
```

immediately before deleting the helper, and abort the move if any non-R2 caller appears. This is a defensive guard because the helper is the only cross-handler utility being migrated.

### 4.7 Route Order Clarification

Codex review also clarified the route-order requirement. Unlike R1 snapshot routes, the 5 R2 routes do not currently collide by path shape. R2 still preserves source declaration order (`effective` → `version` → `convert` → `tree` → `mbom tree`) as a mechanical relocation guard, not because the static paths are currently ambiguous with the dynamic paths.

### 4.8 Pact Provider Required For R2

Taskbook §8 requires running the real Pact provider verifier (not just the CI wiring gate) because R2 moves public routes that appear in the OpenAPI surface. R1 established this precedent.

### 4.9 AUTH_MODE Autouse Fixture Precedent

Taskbook §11 permits (and expects) the implementation PR to add the same `monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")` autouse fixture to any existing tree / convert / effective test file that returns `401` pre-R2 due to middleware-vs-override ordering. Precedent: PR #340 for locale / report router tests, PR #369 for compare-summarized-snapshot tests.

## 5. Decisions NOT Encoded (Deferred)

- R3+ slice ordering is sketched in taskbook §12 for reference but is deferred until R2 lands and reveals any previously hidden helper coupling.
- `BOMConversionService` internals extraction is explicitly not R2; if future work needs service-layer split, it becomes its own taskbook with non-routing scope.
- Shared-dev 142 smoke is out of scope for R2. Any 142 interaction would be tracked separately.

## 6. Verification Commands

This PR is docs-only. Only doc-index contracts apply:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected result: all 3 pass.

## 7. Collaboration Defaults

Per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` §8:

- Claude produced this taskbook + this verification MD as a bounded docs-only increment.
- Codex owns taskbook review (this file and the taskbook itself).
- Only after Codex approves should any R2 implementation PR be opened.

## 8. Known Boundaries

- The taskbook references `main` at `f271102` (post-R1). If `main` advances between this PR and the R2 implementation PR, the implementation PR must re-measure `bom_router.py` endpoint counts and confirm the 5-endpoint tree / effective / version / convert surface is unchanged before executing the split.
- The taskbook does not enumerate every downstream test file by name because new focused tests may land between now and R2 implementation. The implementation PR must grep for `yuantus.meta_engine.web.bom_router.(get_effective_bom|get_bom_by_version|convert_ebom_to_mbom|get_bom_tree|get_mbom_tree|_parse_config_selection)` and repoint all hits.
- The taskbook assumes the R1 seal holds: no `bom_compare_router.py` or compare test is modified by R2 work.

## 9. R1 Post-Merge Audit Summary (Independent)

Before drafting this R2 taskbook, R1 was independently audited on current `main`:

| Check | Result |
| --- | --- |
| `main` HEAD = `f271102` | confirmed |
| 110-test focused regression | `110 passed, 1 warning` |
| Pact provider `test_pact_provider_yuantus_plm.py` | `1 passed, 3 warnings` |
| CI Pact wiring gate | `2 passed` |
| 14 compare endpoints owner = `bom_compare_router` | confirmed, no missing / no wrong-owner |
| `test_bom_delta_preview.py` shape | 211 LOC service-level test on `BOMService.build_delta_preview`; legitimate addition to R1 focused set |

R1 is sealed; R2 proceeds on a validated base.

## 10. Execution Order After This PR

1. Codex reviews the R2 taskbook.
2. R2 implementation PR (`bom_tree_router.py` + 5 handlers moved + contract test + `DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R2_TREE_20260422.md` + CI contracts entry + `_parse_config_selection` migration + any tree / convert / effective test patch-target updates).
3. Post-R2 focused regression and Pact provider verification on `main`.
4. If R2 merges cleanly, the next bounded increment is R3 (children, 2 endpoints) as sketched in taskbook §12 — but only after this cycle's non-technical review points (backlog triage, external signal collection, scheduler decision gate per the next-cycle plan) have been re-assessed.

No bounded increment should combine R2 with any other BOM slice or unrelated file move.
