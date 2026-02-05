# CAD-ML Queue Smoke Report (2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 \
CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 5
- Completed: 5
- Failed: 0
- Cancelled: 0

## Notes
- cad-ml render returned HTTP 422 for DXF; preview fallback still completed jobs.
- Full log: /tmp/verify_cad_ml_queue_smoke_20260205-200432.log
