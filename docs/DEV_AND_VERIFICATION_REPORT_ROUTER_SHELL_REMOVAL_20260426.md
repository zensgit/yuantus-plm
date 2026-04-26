# DEV / Verification — Phase 1 P1.1: report_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.1 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `report_router` compatibility shell from `src/yuantus/api/app.py`
(both the import and the `app.include_router(...)` registration line),
update the portfolio contract entry to mark it unregistered, and migrate
the four owner-router family contracts away from the now-stale
"registered before legacy report_router" assertion.

This is the smallest possible Phase 1 sub-PR — `report_router` had only one
external file referencing it (the portfolio contract itself) — and serves
as the validation slice for the standard recipe.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe (post `8ae1576` patch requiring BOTH import + `include_router` removal).
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` — atomic doc-index discipline.
- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` — backlog state at PR #401 close.

## 3. Recipe Adherence

Followed the standard P1.1 – P1.8 / P1.10 recipe in §5 of the plan MD:

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/report-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | `grep -nE "from yuantus\.meta_engine\.web\.report_router import report_router\b" src/yuantus/api/app.py` and `grep -nE "app\.include_router\(report_router," src/yuantus/api/app.py` | both single-match: line 157 and line 387 |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"` | `app.routes: 671 OK` |
| 5 | Update test files referencing the shell (only `test_router_decomposition_portfolio_contracts.py:88` was an actual reference) | done in step 6 |
| 6 | Update `test_router_decomposition_portfolio_contracts.py` `report_router.py` entry: `registered: True` → `registered: False` | done |
| 7 | Optional shell-module deletion — kept the 5-LOC `src/yuantus/meta_engine/web/report_router.py` file (preserves import path for any external plugin / test that references the module symbol; consistent with `eco_router` shim's "module exists, not registered" pattern) | skipped intentionally |
| 8 | Focused regression | 41 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 157 (`from yuantus.meta_engine.web.report_router import report_router`) and line 387 (`app.include_router(report_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `report_router.py` entry: `"registered": True` → `"registered": False`. The `test_legacy_router_registration_states_are_intentional` test now asserts both the `import_token` and `include_token` are absent in app.py. |
| `src/yuantus/meta_engine/tests/test_report_router_decomposition_closeout_contracts.py` | Removed `"report_router"` from `_ROUTER_REGISTRATION_ORDER`; renamed `test_app_registers_report_routers_in_decomposition_order_before_legacy_shell` → `test_app_registers_report_routers_in_decomposition_order`; added an explicit absence assertion that `app.include_router(report_router,` is no longer in app.py. |
| `src/yuantus/meta_engine/tests/test_report_dashboard_router_contracts.py` | Renamed `test_report_dashboard_router_is_registered_before_legacy_report_router` → `test_report_dashboard_router_is_registered_in_app`. New body asserts the split router is registered AND the legacy is absent. |
| `src/yuantus/meta_engine/tests/test_report_definition_router_contracts.py` | Same rewrite for the `definition` family contract. |
| `src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py` | Same rewrite for the `saved_search` family contract. |
| `src/yuantus/meta_engine/tests/test_report_summary_search_router_contracts.py` | Same rewrite for the `summary_search` family contract. |
| `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry for this MD, alphabetically positioned between `DEV_AND_VERIFICATION_REPORT_ROUTER_DECOMPOSITION_R1_SAVED_SEARCHES_20260424.md` and `DEV_AND_VERIFICATION_REQUIRE_ADMIN_DEPENDENCY_DEDUP_20260421.md`. |

## 5. Verification

Boot check (recipe step 4):

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"
```

Result: `app.routes: 671 OK` (no `ModuleNotFoundError`, no missing-symbol error, all 671 routes load cleanly).

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_report_dashboard_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_definition_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_summary_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **41 passed**.

Whitespace:

```bash
git diff --check
```

Result: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `src/yuantus/api/app.py` has zero `from yuantus.meta_engine.web.report_router import report_router` lines | ✅ |
| 2 | `src/yuantus/api/app.py` has zero `app.include_router(report_router, prefix="/api/v1")` lines | ✅ |
| 3 | `python -c "from yuantus.api.app import create_app; create_app()"` boots cleanly | ✅ (671 routes) |
| 4 | `test_router_decomposition_portfolio_contracts.py` `report_router.py` entry is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes (asserts both tokens absent for unregistered shells) | ✅ |
| 6 | All four owner-family contracts (`dashboard` / `definition` / `saved_search` / `summary_search`) still pass with renamed `_is_registered_in_app` test | ✅ |
| 7 | `test_report_router_decomposition_closeout_contracts.py` passes after dropping `"report_router"` from `_ROUTER_REGISTRATION_ORDER` | ✅ |
| 8 | `test_report_router_permissions.py` (existing legacy-router test) still passes | ✅ |
| 9 | Doc-index trio passes | ✅ |
| 10 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change (no edits to any `*_service.py`).
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/report_router.py` (keeps the import path live for any out-of-tree consumer; deletion can be a follow-up if confirmed unused).
- No edit to other compatibility shells (`bom_router`, `eco_router`, `box_router`, `cutted_parts_router`, `document_sync_router`, `maintenance_router`, `quality_router`, `subcontracting_router`, `version_router`) — each has its own Phase 1 sub-PR.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation here: the optional shell-module deletion (recipe step 7) was deliberately skipped, so the import path `yuantus.meta_engine.web.report_router` still resolves. Only the app.py wiring is removed.
- **Recipe correctness**: this is the first execution of the post-`8ae1576` recipe. The grep verification (step 2) passed first try and `create_app()` boot check (step 4) passed first try, validating that the recipe correctly captures both removal points.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` §3.1 (compat-shell cleanup backlog item)
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` (atomic doc-index discipline applied here)
- PR #387 (file_router shell unregistration precedent)
- Commit `55ffae4` (approvals_router shell unregistration precedent)

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| **P1.1** | **`report_router`** | **✅ this PR** |
| P1.2 | `quality_router` | ⏳ pending opt-in |
| P1.3 | `maintenance_router` | ⏳ pending opt-in |
| P1.4 | `subcontracting_router` | ⏳ pending opt-in |
| P1.5 | `version_router` | ⏳ pending opt-in |
| P1.6 | `box_router` | ⏳ pending opt-in |
| P1.7 | `cutted_parts_router` | ⏳ pending opt-in |
| P1.8 | `bom_router` | ⏳ pending opt-in |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |

Per the plan §18, each sub-PR is its own opt-in gate. The next sub-PR
(P1.2 — `quality_router`) does not auto-start.
