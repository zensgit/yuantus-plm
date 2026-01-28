# Verification - UI Aggregation Regression

Date: 2026-01-28

## Command

```bash
RUN_UI_AGG=1 scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Result Summary

- PASS: 42
- FAIL: 0
- SKIP: 10

Skipped:
- S5-A (CADGF Preview Online) - `RUN_CADGF_PREVIEW_ONLINE=0`
- S5-B (CAD 2D Real Connectors) - `RUN_CAD_REAL_CONNECTORS_2D=0`
- S5-B (CAD 2D Connector Coverage) - `RUN_CAD_CONNECTOR_COVERAGE_2D=0`
- S5-C (CAD Auto Part) - `RUN_CAD_AUTO_PART=0`
- S5-C (CAD Extractor Stub) - `RUN_CAD_EXTRACTOR_STUB=0`
- S5-C (CAD Extractor External) - `RUN_CAD_EXTRACTOR_EXTERNAL=0`
- S5-C (CAD Extractor Service) - `RUN_CAD_EXTRACTOR_SERVICE=0`
- CAD Real Samples - `RUN_CAD_REAL_SAMPLES=0`
- S8 (Ops Monitoring) - `RUN_OPS_S8=0`
- S7 (Tenant Provisioning) - `RUN_TENANT_PROVISIONING=0`

## Output (Tail)

```
PASS: 42  FAIL: 0  SKIP: 10

ALL TESTS PASSED
```
