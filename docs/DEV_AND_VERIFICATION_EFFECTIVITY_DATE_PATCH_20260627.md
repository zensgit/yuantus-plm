# L3-1 — Effectivity date-window PATCH (impl + verification)

> Task: backlog line 3 (CAD-PDM effectivity) → L3-1, per `docs/development/backlog-lines-2-3-4-scoping-taskbook-20260627.md`.
> Branch `claude/effectivity-date-patch` · base `origin/main`.

## What
`PATCH /api/v1/effectivities/{effectivity_id}` — edit a **Date** effectivity's window (`start_date` / `end_date`) in place. Closes the BOM-line-effectivity UPDATE gap (CREATE existed via `bom add_child(effectivity_from/to)`, READ via `/effectivities/items/{id}`; UPDATE/DELETE were missing).

## Scope (v1, narrow — per review)
- **Date only.** A non-Date effectivity → **400** (`EffectivityNotDateError`). No generic Lot/Serial/Unit editing.
- **Elapsed-window guard → 409** (`EffectivityElapsedError`): if the existing record is `effectivity_type == "Date"` and `end_date < now`, the edit is refused. This matches `DateObsoleteService.get_expired_date_effectivities` exactly (Date + `end_date < now`), so a window the **DateObsoleteWorker** may already have swept (wrote a `DateObsoleteImpact`, possibly promoted the Item to Obsolete) cannot be silently *un-expired*. Reconcile-on-edit (retract impact / un-obsolete) is intentionally a later slice; v1 = create a new effectivity instead.
  - The guard keys on the **existing** `end_date`, not the requested new value (so you cannot resurrect a swept window; you *can* shorten a still-open window, even to a past instant, which simply makes it eligible for the next sweep).
- `end_date IS NULL` (open-ended) or a future window → **editable**.
- `start_date >= end_date` (computed new window) → **400**.
- Effectivity not found → **404**. No fields provided → **400**.
- **Create-time protection preserved**: the target item/version must be latest-released and not suspended (`assert_latest_released` / `assert_not_suspended`, same as `create_effectivity`) → **409**. PATCH only edits the date window — it is NOT BOM-line structural CRUD, and a plain item-scoped effectivity is not treated as one.

## Route-count (design-lock)
New route ⇒ app-route count **722 → 723**, synced in lockstep across all four pins: `test_phase4_search_closeout_contracts` (authoritative), `test_breakage_design_loopback_metrics`, `test_metrics_router_route_count_delta` (`EXPECTED_TOTAL_ROUTES`), `test_tier_b_3_breakage_design_loopback_portfolio_contract` (literal string-pin).

## CI wiring (anti-false-green)
`test_effectivity_date_patch_router.py` added to the `ci.yml` contracts list (sorted) **and** a new `detect_changes` **effectivity** case (`effectivity_service.py` / `effectivity_router.py` / `models/effectivity.py` → `run_contracts=true`), so effectivity-surface changes actually run the contracts (not skipped via the `src/*` fall-through — the lesson from the L2-1 lifecycle gap).

## Verification (local)
`PYTHONPATH=<worktree>/src YUANTUS_PYTEST_DB=1 pytest …` — green:
- `test_effectivity_date_patch_router.py`: future-window edit → 200; open-ended edit → 200; elapsed window → 409; non-Date → 400; `start >= end` → 400; 404; no-fields → 400; route registered+owned; **target not-latest-released → 409**; **target suspended → 409**.
- `test_effectivity.py` (service unit) still green; all four route-count pins green at 723; `test_ci_contracts_ci_yml_test_list_order` + `test_ci_change_scope_contracts` green.

## Follow-ups (not in v1)
- Reconcile-on-edit for already-swept windows (retract `DateObsoleteImpact` / un-obsolete) — needs a deliberate worker-interaction design.
- BOM-line effectivity DELETE (the other missing CRUD verb).
