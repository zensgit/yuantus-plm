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
- Preview checks: 5/5 OK (PNG signature, dims >= default DXF threshold 512x512)
- CSV stats appended: /Users/huazhou/Downloads/Github/Yuantus/tmp/cad_ml_queue_stats.csv

## Timing
- elapsed_seconds: 14
- avg_seconds_per_job: 2.80
- throughput_jobs_per_min: 21.43
- avg_job_duration_seconds: 6.22
- min_job_duration_seconds: 0.73
- max_job_duration_seconds: 11.68

## Latest CSV row
```
2026-02-05T14:19:24Z,1770301150,1770301164,14,5,0,0,0,0,2.8,21.428571428571427,6.2185554000000005,0.734868,11.683612,5,6,1,1,1,1,1,256,256,512,512,1,docs/samples/cad_ml_preview_sample.dxf
```

## Notes
- cad-ml docker was not started (RUN_CAD_ML_DOCKER=0); CAD ML base URL not responding, so local preview fallback handled output.
- Full log: /tmp/verify_cad_ml_queue_smoke_dxf_quality_defaults_20260205-221909.log
- Attempted RUN_CAD_ML_DOCKER=1 but Docker daemon was not running. Log: /tmp/verify_cad_ml_queue_smoke_dxf_quality_defaults_docker_20260205-222607.log
