# CAD-ML Queue Smoke Report (DXF + Defaults + CSV, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=0 CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_WORKER_RUNS=6 CAD_ML_QUEUE_MUTATE=1 CAD_ML_QUEUE_CHECK_PREVIEW=1 YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 5
- Completed: 5
- Failed: 0
- Cancelled: 0
- Preview checks: 5/5 OK (PNG signature, dims >= default DXF threshold 256x256)
- CSV stats appended: /Users/huazhou/Downloads/Github/Yuantus/tmp/cad_ml_queue_stats.csv

## Timing
- elapsed_seconds: 14
- avg_seconds_per_job: 2.80
- throughput_jobs_per_min: 21.43
- avg_job_duration_seconds: 6.22
- min_job_duration_seconds: 0.79
- max_job_duration_seconds: 11.66

## Latest CSV row
```
2026-02-05T13:40:58Z,1770298844,1770298858,14,5,0,0,0,0,2.8,21.428571428571427,6.216836,0.793415,11.661026,5,6,1,1,1,1,1,256,256,256,256,1,/Users/huazhou/Downloads/Github/Yuantus/docs/samples/cad_ml_preview_sample.dxf
```

## Notes
- cad-ml docker was not started (RUN_CAD_ML_DOCKER=0); preview fallback handled output.
- Full log: /tmp/verify_cad_ml_queue_smoke_dxf_quality_defaults_20260205-214042.log
