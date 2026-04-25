# DEV / Verification — Phase 1 P1.4: subcontracting_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.4 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `subcontracting_router` compatibility shell from
`src/yuantus/api/app.py` (both the import and the `app.include_router(...)`
registration line), update the portfolio contract entry to mark it
unregistered, drop the now-vestigial shell registration from
`test_subcontracting_router.py`'s test fixture, and migrate the closeout
contract + the three owner-family contracts (orders / analytics /
approval_mapping) away from the now-stale "registered before legacy
subcontracting_router" assertions.

P1.4 follows P1.3's pattern (closeout contract `_ROUTER_REGISTRATION_ORDER`
update + owner-family contract rewrites + real-test fixture cleanup), with
3 owner-family contracts (vs. P1.3's 4).

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe (post `8ae1576`).
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` — P1.1 precedent.
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` — P1.2 precedent.
- `docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_SHELL_REMOVAL_20260426.md` — P1.3 precedent (closest in shape).
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` — atomic doc-index discipline.

## 3. Recipe Adherence

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/subcontracting-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification of both target lines | both single-match: line 194 (import) + line 416 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; create_app()"` | `app.routes: 671 OK` |
| 5 | Update test files: 3 owner-family contracts (orders/analytics/approval_mapping), closeout contract, real router test fixture | done |
| 6 | Update portfolio contract: `subcontracting_router.py` `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 6-LOC `src/yuantus/meta_engine/web/subcontracting_router.py` file (consistent with P1.1/P1.2/P1.3) | skipped intentionally |
| 8 | Focused regression | 38 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 194 (`from yuantus.meta_engine.web.subcontracting_router import subcontracting_router`) and line 416 (`app.include_router(subcontracting_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_subcontracting_router.py` | Removed shell import + `app.include_router(subcontracting_router, prefix="/api/v1")` from `_client_with_db()` fixture. The fixture's 3 split routers (orders/analytics/approval_mapping) are sufficient. |
| `src/yuantus/meta_engine/tests/test_subcontracting_router_decomposition_closeout_contracts.py` | Removed `"subcontracting_router"` from `_ROUTER_REGISTRATION_ORDER`; renamed `test_app_registers_subcontracting_routers_in_decomposition_order_before_legacy_shell` → `test_app_registers_subcontracting_routers_in_decomposition_order`; added explicit absence assertion. |
| `src/yuantus/meta_engine/tests/test_subcontracting_orders_router_contracts.py` | Renamed `test_subcontracting_orders_router_registered_before_legacy_shell` → `test_subcontracting_orders_router_is_registered_in_app`; assert split registered + legacy absent. |
| `src/yuantus/meta_engine/tests/test_subcontracting_analytics_router_contracts.py` | Same rewrite for analytics family contract. |
| `src/yuantus/meta_engine/tests/test_subcontracting_approval_mapping_router_contracts.py` | Same rewrite for approval_mapping family contract. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `subcontracting_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
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
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_orders_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_approval_mapping_router_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **38 passed**.

`git diff --check`: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `app.py` has zero shell import line | ✅ |
| 2 | `app.py` has zero shell `include_router` line | ✅ |
| 3 | `create_app()` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract: `subcontracting_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes | ✅ |
| 6 | Closeout contract registration order list updated; renamed test passes; absence assertion added | ✅ |
| 7 | All 3 owner-family contracts renamed `..._is_registered_in_app` and pass | ✅ |
| 8 | `test_subcontracting_router.py` (real router test) still passes after dropping shell from fixture | ✅ |
| 9 | `test_legacy_subcontracting_router_module_is_registered_shell_only` (closeout contract scanning shell file) still passes | ✅ |
| 10 | Doc-index trio passes | ✅ |
| 11 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/subcontracting_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation: shell-module file kept; only app.py wiring removed.
- **Recipe correctness**: fourth execution of the post-`8ae1576` recipe. All steps passed first try; recipe is now well-validated for the standard P1.x case.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` (P1.1)
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` (P1.2)
- `docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_SHELL_REMOVAL_20260426.md` (P1.3)

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| P1.2 | `quality_router` | ✅ PR #404 |
| P1.3 | `maintenance_router` | ✅ PR #405 |
| **P1.4** | **`subcontracting_router`** | **✅ this PR** |
| P1.5 | `version_router` | ⏳ pending opt-in |
| P1.6 | `box_router` | ⏳ pending opt-in |
| P1.7 | `cutted_parts_router` | ⏳ pending opt-in |
| P1.8 | `bom_router` | ⏳ pending opt-in |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |

Per the plan §18, each sub-PR is its own opt-in gate. The next sub-PR
(P1.5 — `version_router`) does not auto-start.
