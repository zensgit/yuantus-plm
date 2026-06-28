# Dev & Verification — L3 date-obsolete-impacts Fork-B: batch-acknowledge + summary

> Date 2026-06-27 · branch `claude/l3-date-obsolete-fork-b` · **+2 routes (725 → 727)**.

## What & why
Line 3 (CAD-PDM C3 / effectivity ops) Fork-B. The date-obsolete where-used impact ops
surface already supports list / get / single-acknowledge (Slice 2). The #882 taskbook lists
the "fuller operational view" as the next gap. This slice adds the two additive, no-owner-
decision pieces ops asked for:
- `POST /api/v1/cadpdm/date-obsolete-impacts/acknowledge-batch` — acknowledge many impacts in
  one atomic transaction (bulk action). Body `{impact_ids: [...]}`.
- `GET /api/v1/cadpdm/date-obsolete-impacts/summary` — count-by-state aggregate for a dashboard
  (+ optional `?child_obsoleted=true|false` filter).

(The revert/un-acknowledge gap stays **deferred** — it needs an owner decision on audit
semantics; not in this slice.)

## Design decisions
- **Append-only/idempotent, no existence leak.** Batch acknowledges only `open` rows; unknown
  ids and already-`acknowledged` rows are silently skipped (not 404), so re-running is safe.
  Returns only the rows transitioned this call (`acknowledged_count` + `rows`) plus `requested`
  (post-dedup count). Mirrors the single-acknowledge gate + write; never re-triggers obsolete.
- **Summary has a stable shape** — every known state present (0 when none) + `total` — so a
  dashboard renders without probing which states exist. Count-by-state via `func.count` group-by.
- **Route ordering** — `GET /summary` is declared **before** `GET /{impact_id}` so the literal
  "summary" is not captured as an impact id (covered by a dedicated test).
- **Auth** — both reuse `require_admin_permission` (403 for non-admin; tested via a non-admin
  client, asserting no write happens when the gate trips).
- **Route-count** — +2 → **727**, lockstep across all four design-lock pins (`test_phase4_…`
  [the CI-enforced authoritative pin, in the contracts list], `test_breakage_…`,
  `test_metrics_…` `EXPECTED_TOTAL_ROUTES`, `test_tier_b_3_…` string-pin). Both new routes are
  added to the **existing** `date_obsolete_ops_router` (already wired in app.py) — no new
  include.

## Verification
- Local: `PYTHONPATH=<wt>/src YUANTUS_PYTEST_DB=1 pytest` → **26 passed** =
  `test_date_obsolete_wiring.py` (existing ops/worker + 11 new: batch open-only / unknown-skip /
  dedup+idempotent / empty / requires-admin; summary by-state / empty-stable-shape / not-captured-
  as-id / child_obsoleted filter / requires-admin) + `test_phase4_search_closeout_contracts.py`
  (route-count pin at **727**). The other 3 pins verified locally (35 passed in the pin set).
- DB-backed (real in-memory SQLite via the app's `get_db` override + a shared StaticPool session),
  asserting genuine effect (rows flip to acknowledged with actor/timestamp; summary aggregates).
- **Anti-false-green CI wiring**: added a `detect_changes` case for the date-obsolete impacts
  surface (router + model + `test_date_obsolete_wiring.py`) → `run_contracts=true` (empirically
  verified against the real case block); the test is already in the `ci.yml` contracts list, and
  `test_phase4` (route-count) runs in contracts. Without this case, the `src/*` catch-all would
  `continue` on the test/route change and contracts would never run (the documented trap).

## Files
- `src/yuantus/meta_engine/web/date_obsolete_ops_router.py` (+summary +batch-acknowledge routes)
- `src/yuantus/meta_engine/tests/test_date_obsolete_wiring.py` (+11 tests)
- `src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py` + 3 sibling pins (725→727)
- `.github/workflows/ci.yml` (detect_changes date-obsolete-impacts case → run_contracts)
- `docs/DELIVERY_DOC_INDEX.md` (this doc registered)
