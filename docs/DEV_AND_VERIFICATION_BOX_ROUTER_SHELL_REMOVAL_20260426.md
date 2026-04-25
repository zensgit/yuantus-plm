# DEV / Verification — Phase 1 P1.6: box_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.6 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `box_router` compatibility shell from `src/yuantus/api/app.py`,
update the portfolio contract entry to mark it unregistered, drop the
shell registration from `test_box_router.py`'s test fixture, and migrate
the closeout contract away from the now-stale "registered before legacy
box_router" assertion.

P1.6 has the broadest split-router count of Phase 1 so far (10 owner
routers: core / analytics / ops / reconciliation / capacity / policy /
traceability / custody / turnover / aging) — but only 1 closeout contract
to update (no separate per-owner family contracts), making it operationally
simpler than P1.5.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe.
- P1.1–P1.5 precedent MDs.

## 3. Recipe Adherence

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/box-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification of both target lines | both single-match: line 44 (import) + line 315 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; create_app()"` | `app.routes: 671 OK` |
| 5 | Update test files: closeout contract, real router test fixture (`test_box_router.py`) | done |
| 6 | Update portfolio contract: `box_router.py` `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 7-LOC `src/yuantus/meta_engine/web/box_router.py` file | skipped intentionally |
| 8 | Focused regression | 69 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 44 (`from yuantus.meta_engine.web.box_router import box_router`) and line 315 (`app.include_router(box_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_box_router.py` | Removed shell import (line 19) + `app.include_router(box_router, prefix="/api/v1")` (line 42) from `_make_app()`. The 10 split routers (core/analytics/ops/reconciliation/capacity/policy/traceability/custody/turnover/aging) are sufficient. |
| `src/yuantus/meta_engine/tests/test_box_router_decomposition_closeout_contracts.py` | Renamed `test_box_split_routers_registered_before_legacy_router` → `test_box_split_routers_registered_in_app`. New body asserts all 10 split routers registered AND the legacy `box_router` is no longer registered, instead of the obsolete "all split routers come before legacy" ordering. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `box_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_BOX_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry alphabetically positioned. |

## 5. Verification

Boot check:

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"
```

Result: `app.routes: 671 OK`.

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_box_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **69 passed** (the largest regression count yet — driven by the 10 split routers' route surface).

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero shell import line | ✅ |
| 2 | `app.py` has zero shell `include_router` line | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `box_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | Closeout contract: renamed test passes; 10 split routers asserted; legacy absent | ✅ |
| 7 | `test_box_router.py` (real router test) still passes after dropping shell from fixture | ✅ |
| 8 | `test_legacy_box_router_module_is_registered_shell_only` (closeout contract scanning shell file) still passes | ✅ |
| 9 | Doc-index trio passes | ✅ |
| 10 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/box_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **Largest split-router count in P1.x so far** (10 split routers vs 5 in P1.5, 4 in P1.3, 3 in P1.4). All asserted via a single closeout contract (no per-owner family contracts), so the contract update is concentrated.
- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation: shell-module file kept; only app.py wiring removed.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` (P1.1)
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` (P1.2)
- `docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_SHELL_REMOVAL_20260426.md` (P1.3)
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_ROUTER_SHELL_REMOVAL_20260426.md` (P1.4)
- `docs/DEV_AND_VERIFICATION_VERSION_ROUTER_SHELL_REMOVAL_20260426.md` (P1.5)

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| P1.2 | `quality_router` | ✅ PR #404 |
| P1.3 | `maintenance_router` | ✅ PR #405 |
| P1.4 | `subcontracting_router` | ✅ PR #406 |
| P1.5 | `version_router` | ✅ PR #407 |
| **P1.6** | **`box_router`** | **✅ this PR** |
| P1.7 | `cutted_parts_router` | ⏳ pending opt-in |
| P1.8 | `bom_router` | ⏳ pending opt-in |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |
