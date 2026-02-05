# verify_all Regression Report (2026-02-05)

## Command
```
RUN_UI_AGG=1 \
RUN_OPS_S8=1 \
MIGRATE_TENANT_DB=1 \
RUN_CONFIG_VARIANTS=1 \
RUN_CAD_ML_DOCKER=1 \
CAD_PREVIEW_SAMPLE_FILE="$CAD_PREVIEW_SAMPLE_FILE" \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Inputs
- BASE_URL: http://127.0.0.1:7910
- TENANT/ORG: tenant-1 / org-1
- CAD_PREVIEW_SAMPLE_FILE (escaped JSON):
  "/Users/huazhou/Downloads/\u8bad\u7ec3\u56fe\u7eb8/\u8bad\u7ec3\u56fe\u7eb8/ACAD-\u5e03\u5c40\u7a7a\u767d DXF-2013.dxf"
- CAD_ML_BASE_URL: http://127.0.0.1:18000

## Summary
- PASS: 49
- FAIL: 0
- SKIP: 10

## CAD-ML Docker
- Started via `scripts/run_cad_ml_docker.sh` (RUN_CAD_ML_DOCKER=1).
- Health check: OK (status=healthy, services api/ml/redis up).

## Notes
- Full log: /tmp/verify_all_cadml_ci_20260205-093131.log
- cadquery not installed warnings were emitted during CAD conversions but did not fail verification.
- Initial cad-ml health probes saw connection resets before succeeding.
