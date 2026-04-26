# DEV / Verification — Phase 1 P1.8: bom_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.8 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `bom_router` compatibility shell from `src/yuantus/api/app.py`,
update the portfolio contract entry to mark it unregistered, drop the
shell registration from `test_latest_released_guard_router.py`'s test
fixture, and migrate **6 BOM family contracts** away from "registered
before legacy bom_router" / "registered between X and legacy" assertions.

P1.8 has the **most cross-file contract updates of any Phase 1 sub-PR**:
6 family contracts (compare / tree / children / obsolete_rollup /
where_used / substitutes), each with its own previously-asserted ordering
relative to the legacy shell. The legacy ordering (compare → tree →
children → obsolete_rollup → where_used → substitutes → legacy) is the
result of the BOM router decomposition that began with PR #369 and
spanned 6 R-slices.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5.
- P1.1–P1.7 precedent MDs.

## 3. Recipe Adherence

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/bom-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification | both single-match: line 32 (import) + line 304 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; create_app()"` | `app.routes: 671 OK` |
| 5 | Update test files: 6 family contracts + real-test fixture (`test_latest_released_guard_router.py`) | done |
| 6 | Update portfolio contract: `bom_router.py` `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 3-LOC `src/yuantus/meta_engine/web/bom_router.py` file | skipped intentionally |
| 8 | Focused regression | 54 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 32 (`from yuantus.meta_engine.web.bom_router import bom_router`) and line 304 (`app.include_router(bom_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py` | Renamed `test_bom_compare_router_is_registered_before_legacy_bom_router` → `test_bom_compare_router_is_registered_in_app`. Drops legacy ordering, adds explicit absence assertion. |
| `src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py` | Renamed `test_bom_tree_router_is_registered_between_compare_and_legacy` → `test_bom_tree_router_is_registered_after_compare_router`. Preserves the compare→tree ordering check, drops legacy comparison. |
| `src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py` | Renamed `test_bom_children_router_is_registered_between_tree_and_legacy` → `test_bom_children_router_is_registered_after_tree_router`. Preserves compare→tree→children ordering, drops legacy comparison. |
| `src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py` | Renamed `test_bom_obsolete_rollup_router_is_registered_before_legacy` → `test_bom_obsolete_rollup_router_is_registered_after_children_router`. Preserves 4-router ordering chain, drops legacy comparison. |
| `src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py` | Renamed `test_bom_where_used_router_is_registered_before_legacy` → `test_bom_where_used_router_is_registered_after_obsolete_rollup_router`. Preserves 5-router ordering chain. |
| `src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py` | Renamed `test_bom_substitutes_router_is_registered_before_empty_legacy` → `test_bom_substitutes_router_is_registered_after_where_used_router`. Preserves full 6-router ordering chain. |
| `src/yuantus/meta_engine/tests/test_latest_released_guard_router.py` | Removed shell import (line 14) + fixture `include_router` (line 36). The split routers (children + substitutes) cover the test surface. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `bom_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_BOM_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry alphabetically positioned. |

Each family contract test continues to assert the 6-router ordering chain
among the **split** routers (compare → tree → children → obsolete_rollup
→ where_used → substitutes), only the legacy comparison and the test name
are dropped/updated. `test_legacy_bom_router_is_empty_compatibility_shim`
in the substitutes contract (line 175) continues to scan the shell file
unchanged — the shell module file stays.

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
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **54 passed**.

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero shell import line | ✅ |
| 2 | `app.py` has zero shell `include_router` line | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `bom_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | All 6 family contracts: renamed `..._is_registered_after_*` tests pass | ✅ |
| 7 | 6-router ordering chain (compare → tree → children → obsolete_rollup → where_used → substitutes) preserved across the family contracts | ✅ |
| 8 | `test_bom_substitutes_router_contracts.py::test_legacy_bom_router_is_empty_compatibility_shim` still passes (scans shell file) | ✅ |
| 9 | `test_latest_released_guard_router.py` still passes after dropping shell from fixture | ✅ |
| 10 | Doc-index trio passes | ✅ |
| 11 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/bom_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **Most cross-file contract updates yet** — 6 family contracts each with its own
  ordering chain referencing the legacy shell. All 6 rewrites preserve the
  inter-split-router ordering (compare → tree → children → obsolete_rollup
  → where_used → substitutes), only the legacy comparison and assertion
  message are dropped. Recipe scaled cleanly.
- **R1 (plan §12)**: shell removal could break an unknown plugin importer.
  Mitigation: shell-module file kept; only app.py wiring removed.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- P1.1–P1.7 precedent MDs

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
| **P1.8** | **`bom_router`** | **✅ this PR** |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |

Per the plan §18, each sub-PR is its own opt-in gate. The next sub-PR
(P1.9 — `eco_router` re-export shim, special case) does not auto-start.
