# Superseded read-surface — mini Grounding/Scope-lock Taskbook

Date: 2026-06-07
Status: **doc-only** scope-lock. Thin slice that makes B1 (#735) version-axis
semantics **visible** in the read/interface layer. Adds **one public route** (the
first ItemVersion-LIST contract surface) — hence taskbook-first to lock naming /
taxonomy / auth / route-count once. No migration; does NOT touch the B1 state machine.

## 1. Gap (grounded)

B1 landed `ItemVersion.is_superseded` + `state="Superseded"` + the
`is_under_modification` predicate, but the read layer can't surface them:
- `GET /api/v1/versions/items/{item_id}/history` returns the audit `VersionHistory`
  events (the supersede event shows, but not the version *list* with status).
- `/{version_id}/detail` is file-detail; **no endpoint lists an item's `ItemVersion`s
  with their lifecycle status**, and `is_superseded` is serialized nowhere.

## 2. Locked decisions

- **D1 — Route.** `GET /api/v1/versions/items/{item_id}/versions` — on the existing
  `version_lifecycle_router` (`prefix="/versions"`), **parallel to** the `…/history`
  route (`version_lifecycle_router.py:232`). NOT `/items/{item_id}/versions` (keeps the
  item vs version namespaces unmixed).
- **D2 — Response.** Top-level `item_id` + `is_under_modification` (from
  `VersionService.is_under_modification`) + `versions[]`, each row carrying the **raw
  flags** plus one **single-value derived** `lifecycle_status`:
  ```json
  {
    "item_id": "...",
    "is_under_modification": true,
    "versions": [
      {"version_id": "...", "version_label": "2.B", "generation": 2, "revision": "B",
       "branch_name": "main", "state": "Superseded", "is_current": false,
       "is_released": true, "is_superseded": true,
       "lifecycle_status": "historical_released",
       "predecessor_id": "...", "created_at": "...", "released_at": "..."}
    ]
  }
  ```
- **D3 — `lifecycle_status` taxonomy (4 single values; `is_superseded` stays a flag,
  NOT a peer status — avoids a version being both `historical_released` and
  `superseded`):**
  | value | rule |
  |---|---|
  | `active_released` | `is_released and not is_superseded` |
  | `historical_released` | `is_released and is_superseded` |
  | `in_work` | `is_current and not is_released and is_under_modification` |
  | `draft` | otherwise |

  **Evaluation order is FIRST-MATCH and must be written exactly so (so `state ==
  "Superseded"` and `is_current` cannot interfere with the classification):**
  1. `is_released and is_superseded` → `historical_released`
  2. `is_released and not is_superseded` → `active_released`
  3. `not is_released and is_current and is_under_modification` → `in_work`
  4. otherwise → `draft`
- **D4 — No `?status=` filter (v1).** Lists are small → client-side filter suffices;
  server-side filtering would need multi-value / invalid-value / combination semantics
  for little gain. **Deferred** (extension slot, not implemented).
- **D5 — Auth: inherit, not admin.** Use the router's existing `get_current_user_id`
  dependency — which is `get_current_user_id_optional` (aliased at
  `version_lifecycle_router.py:9`), the same dep checkout/checkin/revise/history use.
  A read surface has no reason to be narrower than the mutations. Per-item permission
  tightening, if ever wanted, is a separate security slice.
- **D6 — Service.** Add `VersionService.list_versions(item_id)` (read-only; reuses the
  B1 flags + `is_under_modification`). **Stable sort: `generation ASC, created_at ASC,
  id ASC`** — NOT `(generation, revision)`: `revision` is a string and branch/merge
  scenarios make it unstable, so `created_at`/`id` are the deterministic tie-breakers
  (the response still carries `revision`/`version_label` for version-semantic display).
  **Item-existence check → 404** if missing — do NOT return an empty list and fake
  existence.
- **D7 — Route-count: +1.** Baseline is **706** at this taskbook → impl goes
  **706→707**, but the impl PR's first step MUST **live-recheck** the baseline (main
  moves fast). Bump all **4 route-count pins together** (`test_metrics_router_route_
  count_delta` `EXPECTED_TOTAL_ROUTES`, `test_phase4_search_closeout_contracts`,
  `test_breakage_design_loopback_metrics`, `test_tier_b_3_breakage_design_loopback_
  portfolio_contract`). Also **sweep** `test_version_lifecycle_router_contracts.py`:
  it's a membership check (won't break), but **add the new route to `MOVED_ROUTES`** to
  pin its ownership by `version_lifecycle_router`.
- **D8 — No migration, no B1 change.** Read-only; the B1 state machine /
  `release()` / guard are untouched.

## 3. Verification plan (impl PR, not this doc)

- New tests (dual-registered ci.yml contracts list + conftest allowlist): a seeded
  item with draft / active-released / superseded(historical) / in-work versions →
  each `lifecycle_status` correct; `is_superseded` flag still readable; top-level
  `is_under_modification`; **missing item → 404** (not empty list); stable ordering.
  3–5 tests via `VersionService.list_versions` and/or the router.
- Route-count **706→707** (live-rechecked) with all 4 pins bumped +
  `test_version_lifecycle_router_contracts.MOVED_ROUTES` updated.
- DEV/V doc + index; full CI contracts list green.

## 4. Non-goals

- `?status=` server-side filter (D4 deferred).
- Per-item permission tightening (separate security slice).
- Any write / B1 state-machine change / migration.

## 5. Sequencing

Per owner: this taskbook lands doc-only first; after merge, a single **thin impl**
(`VersionService.list_versions` + router + 3–5 tests + DEV/V). A4-R2
(`exclude_stale_drawings`, policy — its own taskbook) and A3 workstation checkout
(heaviest) remain later, each needing its own opt-in.
