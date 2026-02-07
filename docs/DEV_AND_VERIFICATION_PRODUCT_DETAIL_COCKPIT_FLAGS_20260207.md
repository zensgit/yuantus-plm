# Dev & Verification Report - Product Detail Cockpit Flags (2026-02-07)

This delivery extends the product detail endpoint with opt-in, flag-gated "cockpit" links and
cross-domain summaries so the UI (or scripts) can fetch a product + its readiness/impact entry points
in one call.

## API

Enhanced endpoint:

- `GET /api/v1/products/{item_id}`

New query params:

- `include_impact_summary` (default `false`)
- `include_release_readiness_summary` (default `false`)
- `release_readiness_ruleset_id` (default `readiness`)
- `include_open_eco_hits` (default `false`)
- `cockpit_links_only` (default `true`)

Response additions (only when any flag is enabled):

- `cockpit_links` (stable URLs to cockpit/impact/readiness/eco endpoints)
- `impact_summary` (flagged; returns `{authorized:false}` when Part BOM read is denied)
- `release_readiness_summary` (flagged; admin/superuser only; non-admin returns `{authorized:false}`)
- `open_ecos` (flagged; returns `{authorized:false}` when ECO read is denied)

Notes:

- `cockpit_links_only=true` returns links-only summaries to avoid expensive aggregation by default.
- No breaking changes: default response is unchanged unless flags are set.

## Implementation

- Router:
  - `src/yuantus/meta_engine/web/product_router.py`
- Service:
  - `src/yuantus/meta_engine/services/product_service.py`

## Tests

- New unit tests (mocked, non-DB):
  - `src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py`
- Non-DB allowlist updated:
  - `conftest.py`
- Playwright API-only regression extended:
  - `playwright/tests/product_ui_summaries.spec.js`

## Verification

- Strict gate report (PASS):
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-222534.md`

