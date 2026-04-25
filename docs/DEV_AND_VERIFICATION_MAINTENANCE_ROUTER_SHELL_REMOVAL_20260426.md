# DEV / Verification — Phase 1 P1.3: maintenance_router Shell Removal (2026-04-26)

## 1. Goal

Execute Phase 1 P1.3 of the implementation plan in
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5: remove the
zero-route `maintenance_router` compatibility shell from
`src/yuantus/api/app.py` (both the import and the `app.include_router(...)`
registration line), update the portfolio contract entry to mark it
unregistered, drop the now-vestigial shell registration from
`test_maintenance_router.py`'s test fixture, and migrate the closeout
contract + the four owner-family contracts (category / equipment /
request / schedule) away from the now-stale "registered before legacy
maintenance_router" assertions.

P1.3 is a slightly larger surface than P1.2: 4 owner-family contracts
need rename+rewrite (vs. P1.2's 1 closeout contract) plus the closeout
contract's `_ROUTER_REGISTRATION_ORDER` list update.

## 2. Inputs / Prior Reading

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 — Phase 1 standard recipe (post `8ae1576` patch requiring BOTH import + `include_router` removal).
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` — P1.1 precedent.
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` — P1.2 precedent (first sub-PR with non-contract test fixture impact; same pattern reused here).
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` — atomic doc-index discipline.

## 3. Recipe Adherence

Followed the standard P1.1 – P1.8 / P1.10 recipe in §5 of the plan MD:

| Step | Action | Result |
| --- | --- | --- |
| 1 | `git checkout -b closeout/maintenance-router-shell-removal-20260426 origin/main` | branch at `e4ec310` |
| 2 | grep verification of both target lines in `src/yuantus/api/app.py` | both single-match: line 179 (import) + line 407 (`include_router`) |
| 3 | Remove BOTH lines from `src/yuantus/api/app.py` | done |
| 4 | `python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"` | `app.routes: 671 OK` |
| 5 | Update test files referencing the shell: `test_maintenance_router.py` (real test fixture; removed both shell import and `app.include_router(maintenance_router, ...)` call from `_client_with_db()`), the 4 owner-family contracts (`category`/`equipment`/`request`/`schedule`), and the closeout contract | done |
| 6 | Update `test_router_decomposition_portfolio_contracts.py` `maintenance_router.py` entry: `registered: True` → `False` | done |
| 7 | Optional shell-module deletion — kept the 6-LOC `src/yuantus/meta_engine/web/maintenance_router.py` file (consistent with P1.1/P1.2; closeout contract still uses it as `legacy_module` to verify the shell shape) | skipped intentionally |
| 8 | Focused regression | 46 passed (see §5 below) |
| 9 | This MD + index entry | this PR |

## 4. Files Changed

| Path | Change |
| --- | --- |
| `src/yuantus/api/app.py` | Removed line 179 (`from yuantus.meta_engine.web.maintenance_router import maintenance_router`) and line 407 (`app.include_router(maintenance_router, prefix="/api/v1")`). Net `-2` lines. |
| `src/yuantus/meta_engine/tests/test_maintenance_router.py` | Removed shell import (`from yuantus.meta_engine.web.maintenance_router import maintenance_router`) and the `app.include_router(maintenance_router, prefix="/api/v1")` call from the `_client_with_db()` fixture. The fixture's 4 split routers (category/equipment/request/schedule) are sufficient. |
| `src/yuantus/meta_engine/tests/test_maintenance_router_decomposition_closeout_contracts.py` | Removed `"maintenance_router"` from `_ROUTER_REGISTRATION_ORDER`; renamed `test_app_registers_maintenance_routers_in_decomposition_order_before_legacy_shell` → `test_app_registers_maintenance_routers_in_decomposition_order`; added explicit absence assertion. |
| `src/yuantus/meta_engine/tests/test_maintenance_category_router_contracts.py` | Renamed `test_maintenance_category_router_registered_before_legacy_shell` → `test_maintenance_category_router_is_registered_in_app`; assert split registered + legacy absent. |
| `src/yuantus/meta_engine/tests/test_maintenance_equipment_router_contracts.py` | Same rewrite for equipment family contract. |
| `src/yuantus/meta_engine/tests/test_maintenance_request_router_contracts.py` | Same rewrite for request family contract. |
| `src/yuantus/meta_engine/tests/test_maintenance_schedule_router_contracts.py` | Same rewrite for schedule family contract. |
| `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` | Flipped `maintenance_router.py` entry: `"registered": True` → `"registered": False`. |
| `docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_SHELL_REMOVAL_20260426.md` | This MD. |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry for this MD, alphabetically positioned. |

## 5. Verification

Boot check (recipe step 4):

```bash
.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print('app.routes:', sum(1 for _ in app.routes), 'OK')"
```

Result: `app.routes: 671 OK`.

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_category_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_equipment_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_request_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_schedule_router_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: **46 passed**.

Whitespace:

```bash
git diff --check
```

Result: clean.

## 6. Acceptance Criteria

| # | Check | Status |
| --- | --- | --- |
| 1 | `src/yuantus/api/app.py` has zero `from yuantus.meta_engine.web.maintenance_router import maintenance_router` lines | ✅ |
| 2 | `src/yuantus/api/app.py` has zero `app.include_router(maintenance_router, prefix="/api/v1")` lines | ✅ |
| 3 | `python -c "from yuantus.api.app import create_app; create_app()"` boots cleanly | ✅ (671 routes) |
| 4 | Portfolio contract entry: `maintenance_router.py` is `registered: False` | ✅ |
| 5 | `test_legacy_router_registration_states_are_intentional` passes (asserts both tokens absent) | ✅ |
| 6 | Closeout contract: `_ROUTER_REGISTRATION_ORDER` no longer contains `"maintenance_router"`; renamed `..._in_decomposition_order` test passes; explicit absence assertion passes | ✅ |
| 7 | All 4 owner-family contracts (category/equipment/request/schedule) renamed `..._is_registered_in_app` and pass | ✅ |
| 8 | `test_maintenance_router.py` (real C5 router test) still passes after dropping shell from fixture | ✅ |
| 9 | `test_legacy_maintenance_router_module_is_registered_shell_only` (closeout contract scanning shell file) still passes | ✅ |
| 10 | Doc-index trio passes | ✅ |
| 11 | `git diff --check` clean | ✅ |

## 7. Non-Goals

- No service-layer change.
- No public route / schema / permission / status / tag change.
- No deletion of `src/yuantus/meta_engine/web/maintenance_router.py`.
- No edit to other compatibility shells.
- No Phase 2/3/4/5/6 work.

## 8. Risk Notes

- **R1 (plan §12)**: shell removal could break an unknown plugin importer. Mitigation: shell-module file kept; only app.py wiring removed.
- **Surface size growth vs P1.1/P1.2**: P1.3 has 4 owner-family contracts to update (vs. 4 in P1.1, 0 in P1.2). The recipe scaled cleanly; no recipe modification needed.
- **Recipe correctness**: third execution of the post-`8ae1576` recipe. Grep verification (step 2) and `create_app()` boot check (step 4) both passed first try.

## 9. Cross-References

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §5 (Phase 1 spec)
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_SHELL_REMOVAL_20260426.md` (P1.1 precedent)
- `docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_SHELL_REMOVAL_20260426.md` (P1.2 precedent — same real-test fixture pattern)
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md`

## 10. Phase 1 Progress

| Sub-PR | Shell | Status |
| --- | --- | --- |
| P1.1 | `report_router` | ✅ PR #403 |
| P1.2 | `quality_router` | ✅ PR #404 |
| **P1.3** | **`maintenance_router`** | **✅ this PR** |
| P1.4 | `subcontracting_router` | ⏳ pending opt-in |
| P1.5 | `version_router` | ⏳ pending opt-in |
| P1.6 | `box_router` | ⏳ pending opt-in |
| P1.7 | `cutted_parts_router` | ⏳ pending opt-in |
| P1.8 | `bom_router` | ⏳ pending opt-in |
| P1.9 | `eco_router` (re-export shim) | ⏳ pending opt-in |
| P1.10 | `document_sync_router` | ⏳ pending opt-in |
| P1.11 | Phase 1 closeout MD + portfolio update | ⏳ after P1.10 |

Per the plan §18, each sub-PR is its own opt-in gate. The next sub-PR
(P1.4 — `subcontracting_router`) does not auto-start.
