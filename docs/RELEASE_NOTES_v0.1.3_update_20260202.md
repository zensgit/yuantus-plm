# Release Notes v0.1.3 (Update 2026-02-02)

## Highlights

- Phase 4 baseline enhancements: members, validation, comparison, release, and state fields.
- Phase 5 advanced search & reporting: saved searches, report definitions/executions, dashboards.
- Phase 6 electronic signatures: reasons, manifests, sign/verify/revoke.
- Playwright E2E + CI job for e-sign flow.
- SQLite migration robustness for baseline/report columns.

## Migrations

- `u1b2c3d4e6a9_add_baseline_reports.py`
- `v1b2c3d4e7a0_add_esign_tables.py`

## Configuration

- `ESIGN_SECRET_KEY` (optional; defaults to `JWT_SECRET_KEY` if empty).

## Verification

- Playwright: `Run PLAYWRIGHT-ESIGN-20260202-0813`
- SQLite migration downgrade smoke: `Run MIGRATIONS-SQLITE-DOWNGRADE-20260202-0818`
- Full verification logs: `docs/VERIFICATION_RESULTS.md`
