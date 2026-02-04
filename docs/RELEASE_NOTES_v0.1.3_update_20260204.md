# Release Notes v0.1.3 (Update 2026-02-04)

## Highlights

- Added obsolete BOM scan + resolve (update/new_bom) endpoints.
- Added BOM weight rollup with optional write-back to `properties.weight_rollup`.
- Added verification scripts and Playwright API tests for BOM obsolete + weight rollup.

## Verification

- Script: `bash scripts/verify_bom_obsolete.sh http://127.0.0.1:7910 tenant-1 org-1`
- Script: `bash scripts/verify_bom_weight_rollup.sh http://127.0.0.1:7910 tenant-1 org-1`
- Playwright: `npx playwright test playwright/tests/bom_obsolete_weight.spec.js`
- Full logs: `docs/VERIFICATION_RESULTS.md`
