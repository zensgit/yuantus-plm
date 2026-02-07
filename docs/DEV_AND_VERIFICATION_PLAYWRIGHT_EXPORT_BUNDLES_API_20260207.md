# Dev & Verification: Playwright API-Only Export Bundle Regression

- Date: 2026-02-07
- Scope: PLM (Baseline + Impact + Release Readiness + Item Cockpit)
- Non-goals: CAD editing (explicitly out of scope)

## What Shipped

- Added a Playwright API-only regression spec that validates:
  - Baseline release-diagnostics endpoint is reachable and returns a structured response.
  - Export bundle endpoints return ZIP attachments with correct filenames and ZIP magic bytes.

## Code Changes

- New Playwright spec:
  - `playwright/tests/export_bundles_api.spec.js`

## Verified Scenarios

1. Create a Part via AML.
2. Create a Baseline rooted at the Part.
3. Call baseline release diagnostics:
   - `GET /api/v1/baselines/{baseline_id}/release-diagnostics`
4. Download export bundles and assert attachment filename + ZIP signature:
   - `GET /api/v1/impact/items/{item_id}/summary/export?export_format=zip`
   - `GET /api/v1/release-readiness/items/{item_id}/export?export_format=zip`
   - `GET /api/v1/items/{item_id}/cockpit/export?export_format=zip`

## Verification

- Focused Playwright run:
  - `npx playwright test playwright/tests/export_bundles_api.spec.js`
- Strict gate evidence (PASS):
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-230224.md`
