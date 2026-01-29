# Release Notes v0.1.2 (Update 2026-01-29)

## Regression Update

- Full regression with UI aggregation and config variants:
  - Command: `RUN_UI_AGG=1 RUN_CONFIG_VARIANTS=1 bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
  - Result: PASS=43, FAIL=0, SKIP=10

## Delivery Readiness

- Checklist: `docs/DELIVERY_READINESS_CHECKLIST.md`
- Package layout: `docs/DELIVERY_PACKAGE_LAYOUT.md`
- Production readiness: `docs/PROD_READINESS_CHECK.md`

## References

- Report: `docs/VERIFICATION_RUN_ALL_UI_CONFIG_20260129_1007.md`
- Summary: `docs/VERIFICATION_RESULTS.md`
