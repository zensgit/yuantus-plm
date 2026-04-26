# DEV / Verification — Phase 1 P1.7: cutted_parts_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.7 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `cutted_parts_router` compatibility shell from
`src/yuantus/api/app.py`, update the portfolio contract entry to mark it
unregistered, drop the shell registration from `test_cutted_parts_router.py`'s
test fixture, and migrate **two** decomposition contract files (closeout +
R1) away from "registered before legacy cutted_parts_router" assertions.

P1.7 has 10 split routers (matching P1.6 box) but two contract files share
the legacy assertion (closeout + R1), making it the first P1 sub-PR to
update an R1-style intermediate contract.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5.
- P1.1–P1.6 precedent MDs.

## 3. Recipe Adherence

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/cutted-parts-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification | both single-match: line 59 (import) + line 334 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; create_app()"` | `app.routes: 671 OK` |
| 5 | Update test files: closeout contract + R1 contract + real test fixture | done |
| 6 | Update portfolio contract: `cutted_parts_router.py` `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 7-LOC `src/yuantus/meta_engine/web/cutted_parts_router.py` file | skipped intentionally |
| 8 | Focused regression | 77 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 59 (import) + line 334 (`include_router`). |
| `src/yuantus/meta_engine/tests/test_cutted_parts_router.py` | Removed shell import (line 24) + fixture `include_router` (line 63). |
| `src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_closeout_contracts.py` | Renamed `test_cutted_parts_split_routers_registered_before_legacy_router` → `test_cutted_parts_split_routers_registered_in_app`. Asserts all 10 split routers registered + legacy absent. |
| `src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py` | Renamed `test_cutted_parts_split_routers_registered_before_legacy_router` → `test_cutted_parts_r1_split_routers_registered_in_app`. Preserves the throughput-before-bottlenecks ordering check (R1 source-declaration guard) but drops the legacy comparison and adds explicit absence assertion. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `cutted_parts_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_CUTTED_PARTS_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry alphabetically positioned. |

## 5. Verification

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"
```

Result: `app.routes: 671 OK`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **77 passed**.

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero shell import line | ✅ |
| 2 | `app.py` has zero shell `include_router` line | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `cutted_parts_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | Closeout contract: renamed test passes; 10 split routers asserted; legacy absent | ✅ |
| 7 | R1 contract: renamed test passes; throughput-before-bottlenecks ordering preserved; legacy absent | ✅ |
| 8 | `test_cutted_parts_router.py` (real router test) still passes after dropping shell from fixture | ✅ |
| 9 | `test_legacy_cutted_parts_router_module_is_registered_shell_only` (closeout contract scanning shell file) still passes | ✅ |
| 10 | Doc-index trio passes | ✅ |
| 11 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/cutted_parts_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **First P1 sub-PR with two related decomposition contract files (closeout + R1).** Both updated in lockstep. R1 contract preserves its core source-declaration ordering check (throughput < bottlenecks) — only the legacy comparison and naming change.
- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation: shell-module file kept; only app.py wiring removed.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5
- P1.1–P1.6 precedent MDs

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| P1.2 | `quality_router` | ✅ PR #404 |
| P1.3 | `maintenance_router` | ✅ PR #405 |
| P1.4 | `subcontracting_router` | ✅ PR #406 |
| P1.5 | `version_router` | ✅ PR #407 |
| P1.6 | `box_router` | ✅ PR #408 |
| **P1.7** | **`cutted_parts_router`** | **✅ this PR** |
| P1.8 | `bom_router` | ⏳ pending opt-in |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |
