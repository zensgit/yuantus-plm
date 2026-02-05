# CAD-ML Queue Smoke Report (Multi DWG + Quality, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 \
CAD_ML_QUEUE_REPEAT=6 CAD_ML_QUEUE_WORKER_RUNS=8 CAD_ML_QUEUE_MUTATE=0 \
CAD_ML_QUEUE_SAMPLE_LIST="/Users/huazhou/Downloads/J0924032-02上罐体组件v2.dwg,/Users/huazhou/Downloads/J0225040-00过滤洗涤干燥机.dwg,/Users/huazhou/Downloads/dedup/J0225050-08机罩.dwg" \
CAD_ML_QUEUE_CHECK_PREVIEW=1 \
CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DWG=200 CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DWG=200 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 6 (3 DWG samples, each enqueued twice)
- Completed: 6
- Failed: 0
- Cancelled: 0
- Preview checks: 6/6 OK (PNG signature, dims >= 200x200)

## Timing
- elapsed_seconds: 13
- avg_seconds_per_job: 2.17
- throughput_jobs_per_min: 27.69
- avg_job_duration_seconds: 5.88
- min_job_duration_seconds: 2.13
- max_job_duration_seconds: 9.86

## Notes
- DWG samples are copied without mutation; dedupe re-used the same job id per file.
- Full log: /tmp/verify_cad_ml_queue_smoke_multi_dwg_quality_20260205-205616.log
