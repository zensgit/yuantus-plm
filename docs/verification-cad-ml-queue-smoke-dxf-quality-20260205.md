# CAD-ML Queue Smoke Report (DXF + CSV + Quality, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 \
CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" \
CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_WORKER_RUNS=6 CAD_ML_QUEUE_MUTATE=1 \
CAD_ML_QUEUE_CHECK_PREVIEW=1 \
CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DXF=200 CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DXF=200 \
CAD_ML_QUEUE_STATS_CSV="/tmp/verify_cad_ml_queue_stats_20260205-210155.csv" \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 5
- Completed: 5
- Failed: 0
- Cancelled: 0
- Preview checks: 5/5 OK (PNG signature, dims >= 200x200)
- CSV stats appended: /tmp/verify_cad_ml_queue_stats_20260205-210155.csv

## Timing
- elapsed_seconds: 15
- avg_seconds_per_job: 3.00
- throughput_jobs_per_min: 20.00
- avg_job_duration_seconds: 6.65
- min_job_duration_seconds: 0.88
- max_job_duration_seconds: 12.32

## Notes
- Full log: /tmp/verify_cad_ml_queue_smoke_dxf_quality_20260205-210155.log
