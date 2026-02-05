# CAD-ML Queue Smoke Report (DXF + Defaults + CSV, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_WORKER_RUNS=6 CAD_ML_QUEUE_MUTATE=1 CAD_ML_QUEUE_CHECK_PREVIEW=1 YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 5
- Completed: 5
- Failed: 0
- Cancelled: 0
- Preview checks: 5/5 OK (PNG signature, dims >= default DXF threshold)
- CSV stats appended: /Users/huazhou/Downloads/Github/Yuantus/tmp/cad_ml_queue_stats.csv

## Timing
- elapsed_seconds: 14
- avg_seconds_per_job: 2.80
- throughput_jobs_per_min: 21.43
- avg_job_duration_seconds: 6.39
- min_job_duration_seconds: 0.82
- max_job_duration_seconds: 11.98

## Latest CSV row
```
2026-02-05T13:15:48Z,1770297333,1770297347,14,5,0,0,0,0,2.8,21.428571428571427,6.3936774,0.824531,11.976706,5,6,1,1,1,1,1,200,200,200,200,1,/Users/huazhou/Downloads/Github/Yuantus/docs/samples/cad_ml_preview_sample.dxf
```

## Notes
- Full log: /tmp/verify_cad_ml_queue_smoke_dxf_quality_defaults_20260205-211528.log
