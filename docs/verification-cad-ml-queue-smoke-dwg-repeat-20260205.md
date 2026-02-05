# CAD-ML Queue Smoke Report (DWG repeat=5, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 \
CAD_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/BTJ01230901522-00汽水分离器v1.dwg" \
CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_MUTATE=0 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 5 (same job id returned for each enqueue)
- Completed: 5
- Failed: 0
- Cancelled: 0

## Notes
- `CAD_ML_QUEUE_MUTATE=0` kept the DWG sample unmodified; the API returned the same job id across requests, indicating dedupe behavior.
- Full log: /tmp/verify_cad_ml_queue_smoke_dwg_repeat_20260205-203905.log
