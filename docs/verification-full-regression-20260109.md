# Verification - Full Regression (2026-01-09)

## Environment

- Base URL: http://127.0.0.1:7910
- Tenant: tenant-1
- Org: org-1
- Script: `scripts/verify_all.sh`

## Command

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Results

- Status: ALL TESTS PASSED
- PASS: 33
- FAIL: 0
- SKIP: 10

## Skipped Items (expected)

- CAD 2D Real Connectors (RUN_CAD_REAL_CONNECTORS_2D=0)
- CAD 2D Connector Coverage (RUN_CAD_CONNECTOR_COVERAGE_2D=0)
- CAD Auto Part (RUN_CAD_AUTO_PART=0)
- CAD Extractor Stub/External/Service (flags disabled)
- CAD Real Samples (RUN_CAD_REAL_SAMPLES=0)
- Audit Logs (audit_enabled=false)
- Tenant Provisioning (RUN_TENANT_PROVISIONING=0)
- CADGF Preview Online (RUN_CADGF_PREVIEW_ONLINE=0)
- CAD 2D Preview (CAD ML Vision unavailable)

## Notes

- Version semantics script updated to include tenant/org headers for revision endpoints.
- All core, BOM, ECO, CAD, search, and multi-tenant checks passed.
