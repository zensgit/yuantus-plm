# CAD-ML Queue Smoke Report (Mixed Samples, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 \
CAD_ML_QUEUE_REPEAT=20 CAD_ML_QUEUE_WORKER_RUNS=12 CAD_ML_QUEUE_MUTATE=1 \
CAD_ML_QUEUE_SAMPLE_LIST="/Users/huazhou/Downloads/训练图纸/训练图纸/BTJ01230901522-00汽水分离器v1.dwg,docs/samples/cad_ml_preview_sample.dxf" \
CAD_ML_QUEUE_CHECK_PREVIEW=1 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 20
- Completed: 20
- Failed: 0
- Cancelled: 0
- Preview checks: 20/20 OK (bytes > 1)

## Notes
- DWG samples are copied without mutation; dedupe re-used the same job id for DWG entries.
- DXF entries were mutated (`CAD_ML_QUEUE_MUTATE=1`), producing unique job ids and previews.
- cad-ml render returned HTTP 422 for some DXF renders; fallback preview still completed and preview endpoint returned bytes.
- Full log: /tmp/verify_cad_ml_queue_smoke_mixed_20260205-204305.log
