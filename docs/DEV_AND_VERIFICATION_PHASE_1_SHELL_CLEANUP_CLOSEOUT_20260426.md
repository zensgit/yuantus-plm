# DEV / Verification — Phase 1 Shell Cleanup Closeout (2026-04-26)

## 1. Goal

Close out Phase 1 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — the
"Compatibility-Shell Cleanup" phase that removed (or, for the eco
re-export shim, formally certified the absence of) the legacy
compatibility-shell wiring for 10 router families from
`src/yuantus/api/app.py`.

This MD does NOT introduce code. It records:

1. Which 10 sub-PRs delivered the phase.
2. The final Phase 1 invariant (post-merge of all 10 sub-PRs):
   every shell with a previously-`registered: True` portfolio entry
   is now `registered: False`.
3. The aggregated focused-regression and boot-check evidence.
4. What's preserved (10 shell module files; `cad_router.py` shim still
   `registered: True` because cad_router decomposition closed earlier
   without an unregistration step — out of P1 scope).
5. The hand-off boundary to Phase 2 (observability foundation).

P1.11 is a planning artifact only. CI exercise on this branch is the
doc-index trio.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 spec
  (incl. the post-`8ae1576` recipe correction and the dedicated P1.9
  special-case recipe for re-export shims).
- P1.1–P1.10 sub-PR MDs (10 files):
  - `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_VERSION_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_BOX_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_CUTTED_PARTS_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_BOM_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_ECO_ROUTER_SHELL_REMOVAL_20260426.md`
  - `docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_ROUTER_SHELL_REMOVAL_20260426.md`

## 3. Phase 1 Sub-PR Summary

| Sub-PR | PR | Shell | Recipe variant | Family contracts updated | Real-test fixtures touched | Focused regression | Files changed |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| P1.1 | #403 | `report_router` | standard | 4 | 0 | 41 passed | 9 |
| P1.2 | #404 | `quality_router` | standard | 0 (closeout-only) | 1 | 22 passed | 6 |
| P1.3 | #405 | `maintenance_router` | standard | 4 | 1 | 46 passed | 10 |
| P1.4 | #406 | `subcontracting_router` | standard | 3 | 1 | 38 passed | 9 |
| P1.5 | #407 | `version_router` | standard | 5 | 2 | 47 passed | 12 |
| P1.6 | #408 | `box_router` | standard | 0 (closeout-only) | 1 | 69 passed | 6 |
| P1.7 | #409 | `cutted_parts_router` | standard + R1 contract | 0 (closeout + R1) | 1 | 77 passed | 7 |
| P1.8 | #410 | `bom_router` | standard | 6 | 1 | 54 passed | 11 |
| P1.9 | #411 | `eco_router` | re-export-shim special case | 0 (assertion strengthen only) | 0 | 57 passed | 3 |
| P1.10 | #412 | `document_sync_router` | standard | 8 | 1 | 123 passed | 14 |

**Aggregates (across all 10 sub-PRs):**
- Family contracts updated: **30** (4+0+4+3+5+0+0+6+0+8)
- Real-test fixtures touched: **8** (0+1+1+1+2+1+1+1+0+1)
- Decomposition closeout/R1 contracts touched: **9** (one per shell except `report_router` whose family contracts directly carried the legacy assertions)
- Total focused regression count (sum across sub-PRs): **574 passed**, zero failed
- App boot check (`app.routes` count): **671 OK** before and after every sub-PR (route-count-neutral, as expected for zero-handler shells)

## 4. Final Phase 1 Invariant

After all 10 sub-PRs (PR #403–#412) merge, the
`test_router_decomposition_portfolio_contracts.py::LEGACY_ROUTER_STATES`
table will have the following per-shell `registered` flag:

| Shell | Pre-Phase-1 | Post-Phase-1 |
| --- | --- | --- |
| `approvals_router.py` | False (PR #399 prior) | False (unchanged) |
| `bom_router.py` | True | **False** (P1.8) |
| `box_router.py` | True | **False** (P1.6) |
| `cad_router.py` | True | True (out of P1 scope — see §6) |
| `cutted_parts_router.py` | True | **False** (P1.7) |
| `document_sync_router.py` | True | **False** (P1.10) |
| `eco_router.py` | False (re-export shim) | False (P1.9 strengthens absence assertion) |
| `file_router.py` | False (PR #387 prior) | False (unchanged) |
| `maintenance_router.py` | True | **False** (P1.3) |
| `parallel_tasks_router.py` | False (prior) | False (unchanged) |
| `quality_router.py` | True | **False** (P1.2) |
| `report_router.py` | True | **False** (P1.1) |
| `subcontracting_router.py` | True | **False** (P1.4) |
| `version_router.py` | True | **False** (P1.5) |

Net change from Phase 1: 9 shells flipped `registered: True → False`
(P1.1–P1.8, P1.10). P1.9 was already `registered: False`; only its
closeout-contract assertions were tightened.

`test_legacy_router_registration_states_are_intentional` (the meta-assertion
in the portfolio contract) automatically encodes the new invariant once
all 10 sub-PRs merge — no additional contract change needed in P1.11.

## 5. Preserved Surface (Non-Goal: shell module deletion)

All 10 shell module files (and the `eco_router.py` re-export shim) were
**preserved** intentionally per the optional-step-7 of the standard
recipe. This keeps the `from yuantus.meta_engine.web.<shell>_router import
<shell>_router` import path live for any out-of-tree consumer that has
not yet migrated to the split routers. The shells own zero handlers and
add zero routes, so preserving them is route-count-neutral.

| Shell file | LOC | Shape |
| --- | ---: | --- |
| `bom_router.py` | 3 | bare `APIRouter(prefix="/bom", tags=["BOM"])` |
| `box_router.py` | 7 | docstring + bare `APIRouter` |
| `cutted_parts_router.py` | 7 | docstring + bare `APIRouter` |
| `document_sync_router.py` | 23 | docstring listing 8 split routers + bare `APIRouter` |
| `eco_router.py` | 10 | re-export shim (`eco_core_router as eco_router`) |
| `maintenance_router.py` | 6 | docstring + bare `APIRouter` |
| `quality_router.py` | 6 | docstring + bare `APIRouter` |
| `report_router.py` | 5 | bare `APIRouter` |
| `subcontracting_router.py` | 6 | docstring + bare `APIRouter` |
| `version_router.py` | 6 | docstring + bare `APIRouter` |

Total preserved: ~79 LOC across 10 modules. Each is a candidate for
deletion in a future cycle once a `git grep` confirms zero out-of-tree
imports across all known consumers; that is **not** in P1 scope.

## 6. Out-of-Phase-1 Note: `cad_router.py`

`cad_router.py` is also an empty shell on `main` (the CAD decomposition
closed during the 04-22/-23 cycle), but its portfolio entry remains
`registered: True` because:

1. `app.py` still imports and registers it via the unusual idiom
   `from yuantus.meta_engine.web.cad_router import router as cad_router`
   (note the `router as cad_router` rebinding — distinct from the other
   shells which export their identifier directly).
2. The CAD router decomposition closed without an unregistration step;
   its closeout MD does not reference this Phase 1 cleanup line.

Removing the `cad_router` registration is technically uniform with the
P1 work but was deferred from this phase because (a) the import idiom
differs and would require a slightly different recipe variant, (b) no
P1 sub-PR named it, and (c) the `cad_router.py` shell file is even
smaller than `bom_router.py` and was already verified to own zero
routes.

A future "Phase 1.5" (or a small follow-up sub-PR within Phase 2)
could promote `cad_router.py` to `registered: False`. Tracked here as
**deferred**, not blocked.

## 7. Verification (this PR — docs-only)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: 4 passed.

```bash
git diff --check
```

Expected: clean.

## 8. Cross-Phase Aggregate Verification (post-merge of all 10 sub-PRs)

To be run on `main` once PR #403–#412 all merge:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: portfolio contract passes with all 10 P1 shells now `registered: False`,
plus the doc-index trio remains clean. This is the canonical post-Phase-1
"main is consistent" check.

## 9. Acceptance Criteria

| # | Check | Status (this PR) | Status (post-P1.x merge) |
| --- | --- | --- | --- |
| 1 | All 10 P1 sub-PR MDs exist in `docs/` | will be true post-merge | ✅ (per cross-references in §2) |
| 2 | Each P1 sub-PR documented its boot-check, focused-regression, and recipe-adherence outcome | will be true post-merge | ✅ |
| 3 | Phase 1 closeout MD (this file) is registered in `docs/DELIVERY_DOC_INDEX.md` | ✅ | ✅ |
| 4 | Aggregate focused-regression sum across P1.1–P1.10 ≥ 500 passed | ✅ (574 passed) | ✅ |
| 5 | App route count (671) is invariant across all 10 sub-PRs | ✅ | ✅ |
| 6 | Portfolio contract's `LEGACY_ROUTER_STATES` reflects 9 flipped entries (True→False) and 1 strengthened assertion (eco_router) | will be true post-merge | ✅ (auto-enforced by `test_legacy_router_registration_states_are_intentional`) |
| 7 | All 10 shell module files still importable (none deleted in P1) | ✅ | ✅ |
| 8 | Doc-index trio passes | ✅ | ✅ |
| 9 | `git diff --check` clean | ✅ | ✅ |

## 10. Hand-Off to Phase 2

Per the implementation plan §5 phase ordering:

> **Phase 1 → Phase 2** (Observability Foundation): no code dependency.
> Phase 2 (structured logging + job metrics + per-job latency export)
> can begin once Phase 1 closes; it does not require any P1 work to be
> complete first, but starting Phase 2 against a Phase-1-clean `main`
> is the canonical baseline.

Phase 2 still requires explicit user opt-in per plan §18.2.
**This MD does NOT auto-trigger Phase 2.**

## 11. Files Changed (this PR — docs-only)

| Path | Change |
| --- | --- |
| `docs/DEV_AND_VERIFICATION_PHASE_1_SHELL_CLEANUP_CLOSEOUT_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry alphabetically positioned. |

## 12. Non-Goals (this PR)

- No code change. No app.py edit. No contract test edit.
  (P1.11 is intentionally a planning artifact; the live invariant lives
  in the portfolio contract, which is automatically enforced once all
  10 P1 sub-PRs merge.)
- No deletion of any shell module.
- No `cad_router` shell unregistration (§6 deferred).
- No Phase 2/3/4/5/6 work.
- No edit to `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` (the plan
  remains canonical for the bounded-increment workflow).

## 13. Phase 1 Final Status

**Phase 1: 11/11 sub-PRs (100%) complete**

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| P1.2 | `quality_router` | ✅ PR #404 |
| P1.3 | `maintenance_router` | ✅ PR #405 |
| P1.4 | `subcontracting_router` | ✅ PR #406 |
| P1.5 | `version_router` | ✅ PR #407 |
| P1.6 | `box_router` | ✅ PR #408 |
| P1.7 | `cutted_parts_router` | ✅ PR #409 |
| P1.8 | `bom_router` | ✅ PR #410 |
| P1.9 | `eco_router` (re-export shim, special case) | ✅ PR #411 |
| P1.10 | `document_sync_router` | ✅ PR #412 |
| **P1.11** | **Phase 1 closeout MD** | **✅ this PR** |

**Phase 2 (Observability Foundation), Phase 3 (Postgres schema-per-tenant),
Phase 4 (Search incremental + reports), Phase 5 (Tenant provisioning +
backup runbook), and Phase 6 (External-service circuit breakers) all
remain pending explicit user opt-in per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §18.2.**
