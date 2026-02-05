# CAD-ML Queue Smoke Report (Multi DWG, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 \
CAD_ML_QUEUE_REPEAT=6 CAD_ML_QUEUE_WORKER_RUNS=8 CAD_ML_QUEUE_MUTATE=0 \
CAD_ML_QUEUE_SAMPLE_LIST="/Users/huazhou/Downloads/J0924032-02上罐体组件v2.dwg,/Users/huazhou/Downloads/J0225040-00过滤洗涤干燥机.dwg,/Users/huazhou/Downloads/dedup/J0225050-08机罩.dwg" \
CAD_ML_QUEUE_CHECK_PREVIEW=1 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Jobs enqueued: 6 (3 DWG samples, each enqueued twice)
- Completed: 6
- Failed: 0
- Cancelled: 0
- Preview checks: 6/6 OK (PNG signature, dimensions >= 1)

## Job id distribution
- a30546ca-7da1-497c-87dc-252b0df8483f: 2
- f1bddd40-fc46-4c28-aa0c-818c845cfb6d: 2
- 4064227f-4053-4734-9047-2edf1c187544: 2

## Notes
- DWG samples are copied without mutation; dedupe re-used the same job id per file.
- cad-ml render returned HTTP 422 for some DWG previews; fallback preview still completed and preview endpoint returned PNGs.
- Full log: /tmp/verify_cad_ml_queue_smoke_multi_dwg_20260205-204947.log
