# DEV / Verification — Phase 1 P1.9: eco_router Re-Export Shim Closeout (2026-04-26)

## 1. Goal

Execute Phase 1 P1.9 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — the **special-case
recipe** for the `eco_router` re-export shim.

`eco_router.py` differs structurally from the other 9 P1 shells: it is a
re-export shim (`from yuantus.meta_engine.web.eco_core_router import
eco_core_router as eco_router`), not an empty `APIRouter()` shell. It has
NEVER been imported or registered by `src/yuantus/api/app.py` since the ECO
decomposition completed (the eco_core_router is what the app uses directly).
The portfolio contract has had `eco_router.py` marked `registered: False`
from inception.

Therefore P1.9 has **no app.py edits** and **no test-fixture edits** to
make. The only meaningful work is:

1. Strengthen the existing eco closeout contract to assert the import-line
   absence in `app.py`, achieving full parity with the include-line
   absence assertion already at line 116.
2. Document the special-case via this MD so the Phase 1 audit trail
   contains an entry for every shell, including the structural exception.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard
  recipe (post `8ae1576`) **and** the dedicated P1.9 special-case recipe.
- P1.1–P1.8 precedent MDs.

## 3. Recipe Adherence (special-case)

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/eco-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | Confirm `app.py` does NOT contain `from yuantus.meta_engine.web.eco_router` or `app.include_router(eco_router,` | confirmed — no app.py edits needed |
| 3 | Update test files that import `yuantus.meta_engine.web.eco_router` or alias `eco_router_module` to point at `eco_core_router` directly | repo-wide grep showed only **two** references: the closeout contract's `from yuantus.meta_engine.web import eco_router as eco_shim_module` (load-bearing — used to scan the shim file shape), and the portfolio contract entry. Neither needs migration; both are intentional shim observations. |
| 4 | Update `test_router_decomposition_portfolio_contracts.py` | already `registered: False` (line 68); no change needed |
| 5 | Optional: delete `src/yuantus/meta_engine/web/eco_router.py` | skipped intentionally — preserves the import path for any out-of-tree consumer that uses `from yuantus.meta_engine.web.eco_router import eco_router` |
| 6 | `python -c "from yuantus.api.app import create_app; create_app()"` boot check | `app.routes: 671 OK` |
| 7 | Focused regression | 57 passed (see §5) |
| 8 | This MD + index entry | this PR |

The only **active** code change is one new assertion line added to the
existing `test_app_registers_specialized_eco_routers_before_core_router`
test in `test_eco_router_decomposition_closeout_contracts.py`.

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py` | Added one absence assertion at the end of `test_app_registers_specialized_eco_routers_before_core_router`: `assert "from yuantus.meta_engine.web.eco_router import" not in text`. Companion to the existing `assert "app.include_router(eco_router" not in text` at the same test. |
| `docs/DEV_AND_VERIFICATION_ECO_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry alphabetically positioned. |

**No** edits to `src/yuantus/api/app.py` (eco_router shim is not imported
or registered there). **No** edits to `test_router_decomposition_portfolio_contracts.py`
(eco_router.py entry has been `registered: False` since the ECO decomposition
closed). **No** edits to any test fixture (no real test imports the shim
directly; only the closeout contract uses it as `legacy_module` to verify
the shim shape).

## 5. Verification

Boot check:

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"
```

Result: `app.routes: 671 OK`.

Focused regression (12-file suite covering ECO portfolio + doc-index trio):

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **57 passed**.

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero `from yuantus.meta_engine.web.eco_router import …` lines (asserted by both the portfolio contract via `registered: False`, and now by the closeout contract directly) | ✅ |
| 2 | `app.py` has zero `app.include_router(eco_router, …)` lines | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `eco_router.py` is `registered: False` (was already this state) | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | `test_legacy_eco_router_module_is_shim_only` (closeout contract scanning shim file) still passes | ✅ |
| 7 | `test_app_registers_specialized_eco_routers_before_core_router` (closeout contract) passes with the new import-absence assertion | ✅ |
| 8 | All 7 ECO family contracts (approval_ops/approval_workflow/change_analysis/core/impact_apply/lifecycle/stage) still pass | ✅ |
| 9 | Doc-index trio passes | ✅ |
| 10 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No app.py edit (the shim was never registered there).
- No deletion of `src/yuantus/meta_engine/web/eco_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **Scope is markedly smaller than P1.1–P1.8** because the eco shim was
  already in the desired end-state. The only code delta is one new
  assertion line in an existing closeout-contract test.
- **R1 (plan §12)**: not applicable — no app.py wiring is being changed.
- **No regression risk on the eco family routers** — none of their family
  contracts asserted any "before legacy eco_router" relationship (the
  decomposition closed with eco_core_router as the canonical owner from
  day one).

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec
  including the dedicated P1.9 special-case recipe)
- P1.1–P1.8 precedent MDs (standard shells)
- `src/yuantus/meta_engine/web/eco_router.py` (the re-export shim itself,
  preserved unchanged)

## 10. Phase 1 Progress

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
| **P1.9** | **`eco_router` (re-export shim, special case)** | **✅ this PR** |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |

Per the plan §18, each sub-PR is its own opt-in gate. The next sub-PR
(P1.10 — `document_sync_router`) does not auto-start.
