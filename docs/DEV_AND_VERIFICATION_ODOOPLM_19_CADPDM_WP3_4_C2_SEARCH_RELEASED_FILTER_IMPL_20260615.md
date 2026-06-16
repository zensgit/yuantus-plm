# DEV & Verification: WP3.4 C2 — search latest-released opt-in filter (impl)

Date: 2026-06-15

Implements **WP3.4 C2** as an **opt-in, non-breaking** `released_only` filter on the
item search surface — the "latest-released selection surface" the plan calls for,
*without* changing default search semantics. **No route, no migration, no schema
change** (an optional query param is not a new route — count stays 709).

## Why opt-in (not the audit's proposed fix)

The WP3.4 audit suggested adding `Item.is_released` filters to `SearchService` **and to
`GetOperation`**. Two problems, both avoided here:
1. **`Item` has no `is_released` column** — `is_released` lives on the item's current
   `ItemVersion` (`LatestReleasedGuardService` checks `item.is_current` +
   `version.is_released`). A bare `Item.is_released` filter would not even compile.
2. **Filtering the general `GetOperation` / default search would hide all Draft/WIP
   items** from engineers — a breaking, undesirable change.

So C2 is scoped to an **opt-in flag on search only**; `GetOperation` is untouched.

## As built

- **`SearchService.search(..., released_only=False)`** + **`_search_fallback_db(...,
  released_only=False)`**: when `True`, restrict to the latest-released face —
  `Item.is_current` **and** `Item.current_version_id IN (ItemVersion.id WHERE
  is_released)`. Implemented as a subquery (DB fallback path) and a `{"term":
  {"is_released": True}}` clause (ES path).
- **`_build_doc`** now emits `is_current` + `is_released` (the version-resolved
  latest-released signal, via `_item_is_latest_released`) so the ES `term` filter has a
  field to match. *Caveat:* an existing ES index must be **reindexed** for the ES-mode
  filter to take effect on old docs; the DB fallback path needs no reindex.
- **`search_router.search_items`** gains an optional `released_only: bool = False` query
  param, threaded to the service. Default off ⇒ byte-identical to prior behavior.
- **`GetOperation` is deliberately untouched** — drafts remain gettable/browsable.

## Verification (Python 3.11, no-DB; DB fallback forced)

`test_search_released_only_filter.py` → **3 passed** (forces `svc.client = None`):
- `released_only=True` returns only the current+released item; a current-but-unreleased
  item and a current-but-unversioned item are excluded; `total` reflects the filter.
- **Default (`released_only=False`) is unchanged** — drafts/WIP still returned
  (non-breaking).
- `_build_doc` carries the correct `is_released`/`is_current` signal (released → True;
  unreleased version → False; no version → False).

Blast radius — `search()` gained a defaulted kwarg and `_build_doc` gained additive
keys (both backward-compatible); the **full CI contracts list** was run locally (see
PR for the green count). Test **dual-registered** (`ci.yml` + `conftest.py` allowlist).
Route count unchanged **709**.

## Not in this PR

- No change to `GetOperation` or default search (drafts stay visible).
- No ES auto-reindex (the new `is_released` doc field needs a reindex for ES-mode
  filtering of pre-existing docs; DB fallback is unaffected).
- C3 (date-BOM auto-obsolete) — deferred per owner decision.
