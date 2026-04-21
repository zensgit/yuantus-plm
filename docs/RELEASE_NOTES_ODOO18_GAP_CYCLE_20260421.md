# Release Notes - Odoo18 Gap Cycle - 2026-04-21

## Summary

This update closes the Odoo18 PLM gap-analysis backend cycle that started from `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md`.

The cycle focused on backend parity for the Part / BOM / Rev / ECO / Doc / CAD mainline. It does not enable production schedulers by default and does not add UI work.

## Product Highlights

- Auto numbering is available for item creation paths, with canonical `item_number` behavior and DB-side floor allocation hardening.
- Write-time guards now block invalid downstream usage of non-latest, non-released, or suspended items.
- ECO approval operations gained scheduler-ready escalation coverage and local activation smoke evidence.
- BOM to MBOM synchronization now has a scheduler consumer path and is included in the local activation suite.
- CAD BOM import can aggregate duplicate input edges before commit and preserve localized descriptions.
- BOM UOM behavior is consistent across duplicate guards, compare, where-used, rollup, reports, merge, and MBOM compare.
- Report language selection can consume localized description fields.

## Operational Highlights

- A lightweight scheduler foundation exists, but remains default-off.
- Scheduler smoke coverage includes audit retention, ECO escalation, jobs API readback, and BOM to MBOM activation.
- Shared-dev `142` evidence remains readonly/no-op/default-off; no first-run bootstrap or baseline refreeze is implied.
- Local report/locale router auth test hygiene was fixed so local TestClient coverage matches intended dependency overrides.

## Engineering Closeout

The engineering closeout record is:

- `docs/DEV_AND_VERIFICATION_ODOO18_GAP_CYCLE_CLOSEOUT_20260421.md`

Key backend gap status:

| Gap item | Status |
| --- | --- |
| §一.1 Auto numbering | Closed |
| §一.2 Latest released write-time guard | Closed |
| §一.3 Suspended lifecycle guard | Closed |
| §一.4 ECO escalation scheduler path | Closed for current backend scope |
| §一.5 BOM to MBOM scheduler path | Closed for current backend scope |
| §一.6 BOM dedup + product description i18n | Closed for backend scope |

## Verification

Recent cycle evidence includes:

- PR #339 CI `contracts`: passed; local post-merge scheduler focused set: `27 passed`.
- PR #340 CI `contracts`: passed; local post-merge report/locale focused set: `58 passed`.
- PR #341 CI `contracts`: passed; post-merge doc-index contracts: `3 passed`.

This release-note PR is docs-only and uses doc-index/reference contracts for verification.

## Explicit Non-Goals

- Production scheduler enablement.
- Shared-dev scheduler activation beyond readonly/no-op/default-off smoke.
- UI work for BOM diff, CAD viewer, or approval templates.
- Automatic translation provider integration.
- MES / workorder / sales-side expansion.
- §二 architecture refactors such as router decomposition.

## Next Cycle Candidates

- Stakeholder sign-off using this release note plus the closeout MD.
- §二 router decomposition taskbook.
- UOM-granular transformation rules if operations need exclude/substitute behavior by UOM.
- Production scheduler enablement plan with rollout gates and monitoring.
