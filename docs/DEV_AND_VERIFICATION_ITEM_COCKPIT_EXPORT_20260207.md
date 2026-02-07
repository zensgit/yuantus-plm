# Dev & Verification Report - Item Cockpit + Export Bundle (2026-02-07)

This delivery adds an evidence-grade, cross-domain "item cockpit" API that aggregates:

- Impact summary (where-used + baselines + e-sign summary)
- Strategy-based release readiness (MBOM/Routing/Baseline diagnostics + e-sign manifest status)
- Open ECO hits for the item
- One-click export bundle (zip/json)

## API

New endpoints:

- `GET /api/v1/items/{item_id}/cockpit`
- `GET /api/v1/items/{item_id}/cockpit/export?export_format=zip|json`

Notes:

- v1 access is `admin`/`superuser` only (aligned with the existing release-readiness endpoint).

## Implementation

- Router:
  - `src/yuantus/meta_engine/web/item_cockpit_router.py`
  - `src/yuantus/api/app.py` (router wiring)
- Aggregation sources (reused, no internal HTTP calls):
  - `ImpactAnalysisService` (where-used + baselines + e-sign summary)
  - `ReleaseReadinessService` (release readiness across domains)
  - `ECOService.list_ecos(product_id=item_id)` (open ECO hits)

## Tests

- New unit tests (mocked, non-DB):
  - `src/yuantus/meta_engine/tests/test_item_cockpit_router.py`
- Non-DB allowlist updated:
  - `conftest.py`
- New Playwright API-only spec:
  - `playwright/tests/item_cockpit.spec.js`

## Verification

- Strict gate report (PASS):
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-220207.md`

