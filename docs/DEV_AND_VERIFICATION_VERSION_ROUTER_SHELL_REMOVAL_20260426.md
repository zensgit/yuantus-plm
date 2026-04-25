# DEV / Verification — Phase 1 P1.5: version_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.5 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `version_router` compatibility shell from `src/yuantus/api/app.py`
(both the import and the `app.include_router(...)` registration line),
update the portfolio contract entry to mark it unregistered, drop the
now-vestigial shell registration from two real test fixtures, and migrate
the closeout contract + the five owner-family contracts (revision /
iteration / file / lifecycle / effectivity) away from the now-stale
"registered before legacy version_router" assertions.

P1.5 is the largest Phase 1 surface so far: 5 owner-family contracts
(vs P1.3's 4, P1.4's 3, P1.1's 4, P1.2's 0), 1 closeout contract, 2 real
test fixtures with shell registrations.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe (post `8ae1576`).
- P1.1–P1.4 precedent MDs.
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md`.

## 3. Recipe Adherence

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/version-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification of both target lines | both single-match: line 201 (import) + line 379 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; create_app()"` | `app.routes: 671 OK` |
| 5 | Update test files: 5 owner-family contracts (revision/iteration/file/lifecycle/effectivity), closeout contract, 2 real test fixtures (`test_version_iteration_router.py`, `test_version_revision_router.py`) | done |
| 6 | Update portfolio contract: `version_router.py` `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 6-LOC `src/yuantus/meta_engine/web/version_router.py` file (consistent with P1.1–P1.4) | skipped intentionally |
| 8 | Focused regression | 47 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 201 (`from yuantus.meta_engine.web.version_router import version_router`) and line 379 (`app.include_router(version_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_version_iteration_router.py` | Removed shell import + `app.include_router(version_router, prefix="/api/v1")` from `_client_with_user_id()` fixture. |
| `src/yuantus/meta_engine/tests/test_version_revision_router.py` | Removed shell import + `app.include_router(version_router, prefix="/api/v1")` from `_client_with_db()` fixture. |
| `src/yuantus/meta_engine/tests/test_version_router_decomposition_closeout_contracts.py` | Renamed `test_version_legacy_shell_registered_last` → `test_version_split_routers_registered_in_app`; rewrote body to assert all 5 split routers registered + legacy absent (instead of "all split routers come before legacy" ordering). |
| `src/yuantus/meta_engine/tests/test_version_effectivity_router_contracts.py` | Renamed `test_version_effectivity_router_registered_before_legacy_version_router` → `..._is_registered_in_app`; assert split registered + legacy absent. |
| `src/yuantus/meta_engine/tests/test_version_iteration_router_contracts.py` | Same rewrite for iteration family contract. |
| `src/yuantus/meta_engine/tests/test_version_lifecycle_router_contracts.py` | Same rewrite for lifecycle family contract. |
| `src/yuantus/meta_engine/tests/test_version_file_router_contracts.py` | Same rewrite for file family contract. |
| `src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py` | Same rewrite for revision family contract. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `version_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_VERSION_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry for this MD, alphabetically positioned. |

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
  src/yuantus/meta_engine/tests/test_version_iteration_router.py \
  src/yuantus/meta_engine/tests/test_version_revision_router.py \
  src/yuantus/meta_engine/tests/test_version_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_version_effectivity_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_iteration_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_file_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **47 passed**.

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero shell import line | ✅ |
| 2 | `app.py` has zero shell `include_router` line | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `version_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | Closeout contract: renamed test passes; absence assertion added | ✅ |
| 7 | All 5 owner-family contracts renamed `..._is_registered_in_app` and pass | ✅ |
| 8 | `test_version_iteration_router.py` and `test_version_revision_router.py` (real router tests) still pass after dropping shell from fixtures | ✅ |
| 9 | `test_legacy_version_router_is_empty_shell` (closeout contract scanning shell file) still passes | ✅ |
| 10 | Doc-index trio passes | ✅ |
| 11 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/version_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **Largest P1 surface**: 5 family contracts + closeout + 2 real fixtures. Recipe scaled cleanly without modification.
- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation: shell-module file kept; only app.py wiring removed.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` (P1.1)
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` (P1.2)
- `docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_SHELL_REMOVAL_20260426.md` (P1.3)
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_ROUTER_SHELL_REMOVAL_20260426.md` (P1.4)

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| P1.2 | `quality_router` | ✅ PR #404 |
| P1.3 | `maintenance_router` | ✅ PR #405 |
| P1.4 | `subcontracting_router` | ✅ PR #406 |
| **P1.5** | **`version_router`** | **✅ this PR** |
| P1.6 | `box_router` | ⏳ pending opt-in |
| P1.7 | `cutted_parts_router` | ⏳ pending opt-in |
| P1.8 | `bom_router` | ⏳ pending opt-in |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |

Per the plan §18, each sub-PR is its own opt-in gate. The next sub-PR
(P1.6 — `box_router`) does not auto-start.
