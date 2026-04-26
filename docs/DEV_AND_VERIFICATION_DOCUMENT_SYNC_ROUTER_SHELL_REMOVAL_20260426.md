# DEV / Verification — Phase 1 P1.10: document_sync_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.10 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `document_sync_router` compatibility shell from
`src/yuantus/api/app.py`, update the portfolio contract entry to mark
it unregistered, drop the shell registration from
`test_document_sync_router.py`'s test fixture, and migrate the closeout
contract + **8 owner-family contracts** away from "registered before
legacy document_sync_router" assertions.

P1.10 is the **final standard-shell sub-PR of Phase 1** (P1.11 is the
phase closeout). It has the largest split-router count of all P1 sub-PRs
(8 split routers: analytics / reconciliation / replay_audit / drift /
lineage / retention / freshness / core), the largest LOC shell module
(23 LOC docstring-heavy shim), and 8 family-contract rewrites — yet the
recipe scaled cleanly and produced the largest passing focused regression
of any P1 sub-PR (123 passed).

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe (post `8ae1576`).
- P1.1–P1.9 precedent MDs.

## 3. Recipe Adherence

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/document-sync-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification of both target lines | both single-match: line 109 (import) + line 358 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; create_app()"` | `app.routes: 671 OK` |
| 5 | Update test files: 8 owner-family contracts + closeout contract + real-test fixture | done |
| 6 | Update portfolio contract: `document_sync_router.py` `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 23-LOC `src/yuantus/meta_engine/web/document_sync_router.py` file (consistent with P1.1–P1.9; the shell's docstring documents the 8 split routers and serves as a roadmap for any plugin author still depending on the legacy import path) | skipped intentionally |
| 8 | Focused regression | 123 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 109 (import) + line 358 (`include_router`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_document_sync_router.py` | Removed shell import (line 31) + fixture `include_router` (line 49). The 8 split routers cover the test surface. |
| `src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py` | Removed `"document_sync_router"` from `_ROUTER_REGISTRATION_ORDER`; extended `test_app_registers_document_sync_routers_in_decomposition_order` with explicit absence assertions for both the include_router and import lines. |
| `test_document_sync_analytics_router_contracts.py` | Renamed `..._is_registered_before_legacy_router` → `..._is_registered_in_app`; assert split registered + legacy absent. |
| `test_document_sync_core_router_contracts.py` | Same rewrite (core family). |
| `test_document_sync_drift_router_contracts.py` | Same rewrite (drift family). |
| `test_document_sync_freshness_router_contracts.py` | Same rewrite (freshness family). |
| `test_document_sync_lineage_router_contracts.py` | Same rewrite (lineage family). |
| `test_document_sync_reconciliation_router_contracts.py` | Same rewrite (reconciliation family). |
| `test_document_sync_replay_audit_router_contracts.py` | Same rewrite (replay_audit family). |
| `test_document_sync_retention_router_contracts.py` | Same rewrite (retention family). |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `document_sync_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
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
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_lineage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_retention_router_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **123 passed** (largest P1 focused-regression count).

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero shell import line | ✅ |
| 2 | `app.py` has zero shell `include_router` line | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `document_sync_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | Closeout contract: registration order updated; absence assertions for both import + include_router added | ✅ |
| 7 | All 8 owner-family contracts (analytics/core/drift/freshness/lineage/reconciliation/replay_audit/retention) renamed `..._is_registered_in_app` and pass | ✅ |
| 8 | `test_document_sync_router.py` (real router test) still passes after dropping shell from fixture | ✅ |
| 9 | `test_legacy_document_sync_router_module_is_shell_only` (closeout contract scanning shell file) still passes | ✅ |
| 10 | Doc-index trio passes | ✅ |
| 11 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/document_sync_router.py`.
- No edit to other compatibility shells.
- No Phase 1 closeout MD work (that is P1.11).
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **Largest standard-shell P1 surface**: 8 owner-family contracts + closeout contract + real-test fixture. Recipe scaled cleanly with no modification.
- **Initial run fail-fast caught all 8 family contract regressions in one pass** — recipe step 8 (focused regression) correctly identified each `registered_before_legacy_router` test that needed updating before commit.
- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation: shell-module file kept (with a docstring listing the 8 split routers as a migration roadmap); only app.py wiring removed.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- P1.1–P1.9 precedent MDs

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
| P1.9 | `eco_router` (re-export shim) | ✅ PR #411 |
| **P1.10** | **`document_sync_router`** | **✅ this PR** |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ pending opt-in (after P1.10 merges) |

**All 10 standard-shell sub-PRs done.** Per the plan §18, P1.11 (the Phase 1 closeout MD that summarizes all 10 sub-PR outcomes and possibly tightens the portfolio contract to assert that no `*_router.py` shell is `registered: True` anymore) does not auto-start.
