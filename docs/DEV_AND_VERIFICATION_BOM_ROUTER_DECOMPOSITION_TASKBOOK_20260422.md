# DEV / Verification - BOM Router Decomposition Taskbook - 2026-04-22

## 1. Goal

Record the planning gate for §二 BOM router decomposition, produced under the `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` P1 slot.

This companion MD covers the taskbook-writing PR only. It does not move route code and does not create the R1 implementation PR.

## 2. What This PR Delivers

- `docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_20260422.md` — the taskbook itself, structured to match the #343 parent taskbook cadence.
- `docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_TASKBOOK_20260422.md` — this file.
- `docs/DELIVERY_DOC_INDEX.md` — two new entries registered under the Development & Verification section.

## 3. What This PR Does NOT Deliver

- No change to `src/yuantus/meta_engine/web/bom_router.py`.
- No new file `bom_compare_router.py`.
- No change to `src/yuantus/api/app.py`.
- No new or modified tests other than doc-index contracts.
- No change to `.github/workflows/ci.yml`.
- No change to the plugin `yuantus-bom-compare` surface.
- No change to any BOM service-layer code.
- No CAD / file / ECO / scheduler router changes.

## 4. Decisions Encoded In The Taskbook

### 4.1 R1 Slice = BOM Compare Routes (14 endpoints)

The taskbook locks R1 to the 14 endpoints rooted at `/api/v1/bom/compare*`, with exact method + path entries in §4 of the taskbook. Rationale:

- Largest cohesive group among the 29 BOM router endpoints (≈ half the routes).
- Uses a dedicated prefix family, so there is no path ambiguity at registration time.
- Uses comparator DTOs that do not leak into tree / obsolete / children / substitutes surfaces.
- Post-PR #334 and PR #337, UOM-aware compare behavior is stable. R1 should produce zero behavior change.

### 4.2 R1 Forbids Business Logic Change

Taskbook §5 / §9 / §10 explicitly forbid modifying:

- comparator implementations (service-layer);
- plugin `yuantus-bom-compare`;
- request / response schema;
- permission / tag / HTTP status;
- helpers or DTOs used by non-compare handlers.

The reason is to keep the diff mechanical and independently rollback-able.

### 4.3 Route Ownership Contract Required

Taskbook §7 requires a dedicated `test_bom_compare_router_contracts.py` that asserts:

- module ownership per moved path,
- legacy absence in `bom_router.py`,
- registration order in `app.py`,
- path uniqueness in the FastAPI app,
- tag preservation,
- snapshot route declaration ordering for static `/snapshots/compare` routes before dynamic `/{snapshot_id}` routes.

Contract style must mirror the CAD R1–R12 contracts so reviewer diffs are minimal.

### 4.4 Public API Paths Unchanged

Taskbook §6 pins every public URL. Any client calling `GET /api/v1/bom/compare*` today must continue to work without change, including query params, response shape, and status codes.

### 4.5 Codex Review Remediation

Codex review found three taskbook-level gaps and patched them before approval:

- The original focused regression set omitted existing direct compare route tests (`test_bom_delta_router.py`, `test_bom_summarized_router.py`, and snapshot compare/snapshot CRUD router tests). R1 now must run these tests and update stale `patch("yuantus.meta_engine.web.bom_router.compare_bom")` targets to `bom_compare_router` where needed.
- The original pact provider command pointed only at the CI wiring gate. R1 now must run the real provider verifier `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`, with `test_ci_contracts_pact_provider_gate.py` retained as the workflow wiring gate when CI YAML changes.
- The original endpoint table listed dynamic snapshot routes before static snapshot compare routes. R1 now explicitly preserves source declaration order so `/snapshots/compare` cannot be captured as a `{snapshot_id}` path.

## 5. Decisions NOT Encoded (Deferred)

- R2+ slice ordering is sketched in taskbook §12 as a reference, but the precise boundaries are deferred until R1 lands and reveals actual service coupling.
- `BOMCompareService` extraction is explicitly not R1; when needed it becomes its own taskbook with a non-routing scope.
- Shared-dev 142 smoke is out of scope; no 142 interaction is required for either the taskbook PR or the R1 implementation PR.

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

Per `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` §8:

- Claude produced this taskbook + this verification MD as a bounded docs-only increment.
- Codex owns taskbook review (this file and the taskbook itself).
- Only after Codex approves should any R1 implementation PR be opened.

## 8. Known Boundaries

- The taskbook references the `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` structure. If that plan is amended later (for example, by inserting a new priority before P1), the taskbook numbering references remain pointed at "P1" as the intended slot.
- The taskbook assumes `main` at PR #364 state. If `main` advances between now and R1 implementation, the R1 PR must re-measure `bom_router.py` line counts and confirm the 14-endpoint compare surface is unchanged before executing the split.
- The taskbook does not enumerate private helpers by name because their identity depends on future implementation reading; they are identified by usage scope (compare-only vs shared).

## 9. Execution Order After This PR

1. Codex review of the taskbook.
2. R1 implementation PR (`bom_compare_router.py` + 14 handlers moved + contract test + `DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R1_COMPARE_20260422.md`).
3. Post-R1 focused regression and pact provider verification.
4. If R1 merges cleanly, R2+ taskbook (tree / effective / version / convert) as a follow-up.

No bounded increment should combine R1 with any other BOM slice or unrelated file move.
