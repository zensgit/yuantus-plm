# Dev + Verification Report (CAD-ML verify_all, 2026-02-05)

## Summary
- Stabilized cad-ml auto-start in `verify_all.sh` by using repo-root paths for helper scripts.
- Added retry logic to cad-ml health checks to absorb early connection resets.
- Re-ran full verify_all regression with cad-ml docker enabled (PASS).

## Changes
- `scripts/verify_all.sh`: run/stop cad-ml helper scripts using `${REPO_ROOT}/scripts/...` to work under piped execution.
- `scripts/check_cad_ml_docker.sh`: retry health probe (`CAD_ML_HEALTH_RETRIES`, `CAD_ML_HEALTH_SLEEP_SECONDS`).

## Verification
Command:
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

Results:
- PASS: 49
- FAIL: 0
- SKIP: 10

Log:
- `/tmp/verify_all_cadml_ci_20260205-093131.log`

Notes:
- cad-ml docker health initially returned connection resets before succeeding (now retried).
- `cadquery` not installed warnings occurred during CAD conversions but did not fail verification.
