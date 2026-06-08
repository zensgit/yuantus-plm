# DEV & Verification: OdooPLM 19 CAD-PDM Superseded read-surface (impl)

Date: 2026-06-07

Implements the thin **Superseded read-surface** from the ratified scope-lock taskbook
`DEVELOPMENT_ODOOPLM_19_CADPDM_SUPERSEDE_READ_SURFACE_TASKBOOK_20260607.md` (#740) —
the follow-on the B1 closeout flagged ("Any Superseded read-surface … would be a
separate slice"). Makes the **B1** (#735) version-axis semantics
(`is_superseded` / `state="Superseded"` / `is_under_modification`) **visible** in the
read layer via the first `ItemVersion`-LIST contract surface. **One new route;
read-only; no migration; the B1 state machine / `release()` / guard are untouched.**

## Live re-check (per D7 — main moves fast)

- **Route baseline = 706** (live-confirmed: `test_metrics_router_route_count_delta`
  failed `707 == 706` after the route was added, i.e. baseline was exactly 706). The
  new route → **706 → 707**; all 4 route-count pins bumped together.
- **Single Alembic head = `b1_supersede_001`** (unchanged; this slice adds **no
  migration** — read-only over the B1 columns).

## As built (against the ratified decisions)

- **D1 — route.** `GET /api/v1/versions/items/{item_id}/versions` on the existing
  `version_lifecycle_router` (`prefix="/versions"`), **parallel to** `…/history`
  (`version_lifecycle_router.py`). Item vs version namespaces stay unmixed.
- **D2 — response.** Top-level `item_id` + `is_under_modification` (from
  `VersionService.is_under_modification`) + `versions[]`; each row carries the **raw
  flags** (`is_current` / `is_released` / `is_superseded` / `state` /
  `version_label` / `generation` / `revision` / `branch_name` / `predecessor_id` /
  `created_at` / `released_at`) **plus** one **single-value derived** `lifecycle_status`.
- **D3 — `lifecycle_status` taxonomy.** 4 single values, with `is_superseded` kept a
  **flag, not a peer status** (a version is never both `historical_released` AND
  `superseded`). Evaluation is **FIRST-MATCH, written exactly so** a stale
  `state=="Superseded"` / `is_current` cannot skew the classification:
  1. `is_released and is_superseded` → `historical_released`
  2. `is_released and not is_superseded` → `active_released`
  3. `not is_released and is_current and is_under_modification` → `in_work`
  4. otherwise → `draft`
- **D4 — no `?status=` filter (v1).** Client-side filter suffices for small lists;
  deferred (extension slot, not implemented).
- **D5 — auth: inherit, not admin.** The route uses the router's existing
  `get_current_user_id` dep (= `get_current_user_id_optional`), the SAME dep
  checkout/checkin/revise use — a read surface no narrower than the mutations. (In the
  default `required` auth mode the dep still 401s without a token, identical to the
  mutations; per-item permission tightening is a separate security slice.)
  **Asymmetry flagged for review:** the taskbook D5 cited "the same dep …/history
  uses", but `get_history` (`version_lifecycle_router.py:233`) actually has **no** auth
  dep — so this `/versions` read is **authed while its closest peer `…/history` serves
  unauthenticated**. The implementation follows D5's *explicit* instruction (add the
  dep / match the mutations); the owner should confirm intent at review — keep
  `/versions` authed (i.e. `/history` is the oversight), or drop the dep to match
  `/history`. Either is a one-line change; no other code depends on the choice.
- **D6 — `VersionService.list_versions(item_id)`.** Read-only; reuses the B1 flags +
  `is_under_modification`. Item-existence check → raises a "not found" `VersionError`
  (router → **404**), **never a faked empty list**. **Stable sort: `generation ASC,
  created_at ASC, id ASC`** — NOT `(generation, revision)`: `revision` is a string and
  branch/merge makes it unstable, so `created_at`/`id` are the deterministic
  tie-breakers (the row still carries `revision`/`version_label` for display).
- **D7 — route-count +1 (706 → 707).** All **4 pins bumped together**
  (`test_metrics_router_route_count_delta.EXPECTED_TOTAL_ROUTES`,
  `test_phase4_search_closeout_contracts`, `test_breakage_design_loopback_metrics`,
  and the meta-cross-reference in
  `test_tier_b_3_breakage_design_loopback_portfolio_contract` — its asserted literal
  `"len(app.routes) == 707"` + the `_706`→`_707` function rename). The new route is
  also added to `test_version_lifecycle_router_contracts.MOVED_ROUTES` to pin its
  ownership by `version_lifecycle_router` (it passes the owner / once-registered /
  `Versioning`-tag contracts).
- **D8 — no migration, no B1 change.** Read-only; the B1 state machine / `release()` /
  D4b guard are untouched.

## Verification (Python 3.11 venv, requirements.lock)

- **`test_version_list_read_surface.py` → 6 passed** (new; dual-registered): missing
  item → **404** (not empty list); the **four-state taxonomy** (one item carrying
  `historical_released` + `active_released` + `in_work`, a second item's lone
  never-released draft → `draft`); **`in_work` is DERIVED** from
  `is_under_modification` (two byte-identical open drafts classify differently solely
  on the predicate); **`is_superseded` flag preserved** alongside the derived status
  (and a realistic `state="Superseded"` row still classifies via the flags, not the
  string); **stable sort** `generation ASC, created_at ASC, id ASC` (scrambled seed
  with hand-set `created_at`/ids so each key is the decider for a distinct pair);
  **router serialization + 404** over `TestClient`.
- Route-count **706 → 707** (live-rechecked) with all 4 pins green +
  `test_version_lifecycle_router_contracts` (MOVED_ROUTES) green.
- Blast-radius run (new + the 4 pins + lifecycle contracts + `test_version_supersede_b1`
  + `test_version_service`) → **72 passed** (B1 + the service tests unaffected).
- Test **dual-registered** (`ci.yml` contracts list + `conftest.py` no-DB allowlist;
  note `pytest_ignore_collect` is a no-op under pytest 9.0.3, so `ci.yml` is the real
  gate — the allowlist mirrors the `test_version_supersede_b1` precedent).
- DEV/V doc indexed in `DELIVERY_DOC_INDEX.md`. `git diff --check` clean.

## Not in this PR

- `?status=` server-side filter (D4 deferred — extension slot).
- Per-item permission tightening on the read (separate security slice).
- **Multi-branch `in_work`:** the item-level `is_under_modification` is applied to
  every row, so a 2nd open-current draft on a *non-main branch* (the per-`(item,
  branch)` partial-unique allows it) would also read `in_work`. Accepted v1 limitation
  — branch/workstation workflows are A3 (deferred).
- Any write / B1 state-machine change / migration.
- **A4-R2** (`exclude_stale_drawings` policy) and **A3** workstation checkout — each
  remains its own taskbook + opt-in.
