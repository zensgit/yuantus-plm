# Delivery Release Summary (2026-02-02)

## Scope Highlights

- Baseline enhancements (members, validation, comparison, release).
- Advanced search & reporting (saved searches, report definitions/executions, dashboards).
- Electronic signatures (reasons, manifests, sign/verify/revoke, audit logs).
- Report export (CSV/JSON), baseline comparison details endpoint, audit log query.

## Key Endpoints Added

- `POST /api/v1/reports/definitions/{report_id}/export`
- `GET /api/v1/baselines/comparisons/{comparison_id}/details`
- `GET /api/v1/esign/audit-logs`

## Verification Summary

- Pytest non-DB + DB: PASS (see `docs/VERIFICATION_RESULTS.md`)
- Playwright E-sign E2E: PASS

## Delivery Artifacts

- Package: `YuantusPLM-Delivery_20260202.tar.gz` / `.zip`
- Checksums: `.sha256`
- Docs index: `docs/DELIVERY_DOC_INDEX.md`
