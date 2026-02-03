# Release Notes v0.1.3 (Update 2026-02-03)

## Highlights

- Baseline effective-date lookup endpoint for released baselines.
- Baseline list API now supports filtering by type/scope/state/effective date.
- E-sign signing reason update/deactivate support and meaning filter.
- Advanced search filter operators: startswith, endswith, not_contains.
- Delivery API examples refreshed to cover new endpoints and filters.
- Regression verification scripts now auto-align env/storage and tenant DB resolution to the running server.

## Verification

- Pytest: `Run PYTEST-NON-DB-20260203-0856`
- Pytest (DB): `Run PYTEST-DB-20260203-0856`
- Playwright: `Run PLAYWRIGHT-ESIGN-20260203-0856`
- Verify-all (audit + UI + Ops): `Run VERIFY-ALL-20260203-155637`
- Full regression (all optional CAD/extractor/provisioning): `Run FULL-REGRESSION-20260203-155800`
- Full logs: `docs/VERIFICATION_RESULTS.md`
