# Release Announcement v0.1.3 (Update 2026-02-03)

## Summary

This update adds baseline effective-date lookup, improves e-sign reason maintenance, and extends advanced search filter operators.

## Highlights

- Baseline effective-date lookup endpoint for released baselines.
- E-sign signing reason update/deactivate support and meaning filter.
- Advanced search filter operators: startswith, endswith, not_contains.
- Updated API examples for new endpoints and filters.

## Verification

- Pytest: `Run PYTEST-NON-DB-20260203-0856`
- Pytest (DB): `Run PYTEST-DB-20260203-0856`
- Playwright: `Run PLAYWRIGHT-ESIGN-20260203-0856`
- Full logs: `docs/VERIFICATION_RESULTS.md`
