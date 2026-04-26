# DEV / Verification — Phase 1 P1.2: quality_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.2 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `quality_router` compatibility shell from `src/yuantus/api/app.py`
(both the import and the `app.include_router(...)` registration line),
update the portfolio contract entry to mark it unregistered, migrate the
single quality decomposition closeout contract away from the now-stale
"registered before legacy quality_router" assertion, and drop the now-vestigial
shell registration from `test_quality_router.py`'s test fixture.

P1.2 mirrors the P1.1 (`report_router`) recipe but is slightly broader: in
addition to the contract test updates, P1.2 also removes a real-test fixture's
shell-registration call. `quality_router.py` (the 6-LOC shell file) is kept
intact, consistent with P1.1.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe (post `8ae1576` patch requiring BOTH import + `include_router` removal).
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` — P1.1 precedent (smaller, no real-test fixture impact).
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` — atomic doc-index discipline.

## 3. Recipe Adherence

Followed the standard P1.1 – P1.8 / P1.10 recipe in §5 of the plan MD:

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/quality-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | `grep -nE "from yuantus\.meta_engine\.web\.quality_router import quality_router\b" src/yuantus/api/app.py` and `grep -nE "app\.include_router\(quality_router," src/yuantus/api/app.py` | both single-match: line 183 and line 411 |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"` | `app.routes: 671 OK` |
| 5 | Update test files referencing the shell: `test_quality_router.py` (real test fixture; removed both the shell import and the `app.include_router(quality_router, ...)` call from the fixture) and `test_router_decomposition_portfolio_contracts.py` (handled in step 6) | done |
| 6 | Update `test_router_decomposition_portfolio_contracts.py` `quality_router.py` entry: `registered: True` → `registered: False` | done |
| 7 | Optional shell-module deletion — kept the 6-LOC `src/yuantus/meta_engine/web/quality_router.py` file (consistent with P1.1's "preserves import path" choice; closeout contract still uses it as `legacy_module` to verify the shell shape) | skipped intentionally |
| 8 | Focused regression | 22 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 183 (`from yuantus.meta_engine.web.quality_router import quality_router`) and line 411 (`app.include_router(quality_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_quality_router.py` | Removed shell import (`from yuantus.meta_engine.web.quality_router import quality_router`) and the `app.include_router(quality_router, prefix="/api/v1")` call from the `_client_with_db()` fixture. The fixture's 3 split routers (`quality_points_router`, `quality_checks_router`, `quality_alerts_router`) are sufficient to exercise the test surface; the shell registration was vestigial (zero handlers). |
| `src/yuantus/meta_engine/tests/test_quality_router_decomposition_closeout_contracts.py` | Renamed `test_quality_split_routers_registered_before_legacy_quality_router` → `test_quality_split_routers_registered_in_app`. New body asserts the 3 split routers are registered AND the legacy `quality_router` is no longer registered, instead of the obsolete "all split routers come before legacy" ordering check. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `quality_router.py` entry: `"registered": True` → `"registered": False`. The existing `test_legacy_router_registration_states_are_intentional` test now asserts both the `import_token` and `include_token` are absent in app.py. |
| `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry for this MD, alphabetically positioned between `DEV_AND_VERIFICATION_QUALITY_ROUTER_DECOMPOSITION_CLOSEOUT_20260424.md` and `DEV_AND_VERIFICATION_QUOTA_ENFORCEMENT_E2E_20260213.md`. |

## 5. Verification

Boot check (recipe step 4):

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"
```

Result: `app.routes: 671 OK` (same as P1.1; shell had zero routes so removal is route-count-neutral).

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **22 passed**.

Whitespace:

```bash
git diff --check
```

Result: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `src/yuantus/api/app.py` has zero `from yuantus.meta_engine.web.quality_router import quality_router` lines | ✅ |
| 2 | `src/yuantus/api/app.py` has zero `app.include_router(quality_router, prefix="/api/v1")` lines | ✅ |
| 3 | `python -c "from yuantus.api.app import create_app; create_app()"` boots cleanly | ✅ (671 routes) |
| 4 | `test_router_decomposition_portfolio_contracts.py` `quality_router.py` entry is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes (asserts both tokens absent for unregistered shells) | ✅ |
| 6 | `test_quality_router_decomposition_closeout_contracts.py::test_quality_split_routers_registered_in_app` passes; old `..._before_legacy_quality_router` removed | ✅ |
| 7 | `test_quality_router.py` (the real C4/C8 router test) still passes after dropping the shell `include_router` from the fixture | ✅ |
| 8 | `test_legacy_quality_router_is_empty_shell` (closeout contract that scans the shell file for `@quality_router.*` decorators) still passes | ✅ |
| 9 | Doc-index trio passes | ✅ |
| 10 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change (no edits to `quality_service.py` or any other `*_service.py`).
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/quality_router.py` (keeps the import path live for any out-of-tree consumer; deletion can be a follow-up if confirmed unused).
- No edit to other compatibility shells (`bom_router`, `eco_router`, `box_router`, `cutted_parts_router`, `document_sync_router`, `maintenance_router`, `report_router`, `subcontracting_router`, `version_router`) — each has its own Phase 1 sub-PR.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation here: optional shell-module deletion (recipe step 7) was deliberately skipped, so the import path `yuantus.meta_engine.web.quality_router` still resolves. Only the app.py wiring is removed.
- **Real-test fixture impact (new vs P1.1)**: P1.2 is the first P1 sub-PR with a non-contract test importing the shell. The shell registration in `test_quality_router._client_with_db()` was vestigial (the shell has zero handlers) — its removal is route-count-neutral. The 5 behavior tests + 1 manufacturing-context test continue to pass against the 3 split routers alone, which proves the shell registration was redundant.
- **Recipe correctness**: second execution of the post-`8ae1576` recipe. Grep verification (step 2) and `create_app()` boot check (step 4) both passed first try. The recipe correctly catches a slightly broader case (real-test fixture) without modification.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` (P1.1 precedent)
- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` §3.1 (compat-shell cleanup backlog item)
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` (atomic doc-index discipline applied here)
- PR #387 (file_router shell unregistration precedent)
- Commit `55ffae4` (approvals_router shell unregistration precedent)

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| **P1.2** | **`quality_router`** | **✅ this PR** |
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
(P1.3 — `maintenance_router`) does not auto-start.
