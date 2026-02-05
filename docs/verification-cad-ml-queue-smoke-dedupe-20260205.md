# CAD-ML Queue Smoke Report (Dedupe Compare, 2026-02-05)

## Commands

### Mutate disabled (dedupe expected)
```
RUN_CAD_ML_DOCKER=1 \
CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" \
CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_WORKER_RUNS=6 CAD_ML_QUEUE_MUTATE=0 \
CAD_ML_QUEUE_CHECK_PREVIEW=1 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

### Mutate enabled (unique jobs expected)
```
RUN_CAD_ML_DOCKER=1 \
CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" \
CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_WORKER_RUNS=6 CAD_ML_QUEUE_MUTATE=1 \
CAD_ML_QUEUE_CHECK_PREVIEW=1 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Mutate=0: 5/5 completed, single job id reused across all enqueues (dedupe confirmed).
- Mutate=1: 5/5 completed, 5 unique job ids (dedupe avoided).
- Preview checks: 10/10 OK (PNG signature, dimensions >= 1)

## Job id distribution
- Mutate=0: 71a2ff5d-4da1-4340-961a-c0ff8a77dd7d x5
- Mutate=1: 2ae9bec1-3376-4b9a-bc85-2b7ded75d181, 05fb2320-a7fa-4193-9b17-4bc7bcb66969, 516eaab6-f6e8-4a9e-983e-0ba387fc7351, 47286070-3d18-4b21-a595-2f5073e92659, cb7f6e1a-8c43-475f-8692-909896463218

## Notes
- Mutate=0 log: /tmp/verify_cad_ml_queue_smoke_dedupe_mutate0_20260205-205011.log
- Mutate=1 log: /tmp/verify_cad_ml_queue_smoke_dedupe_mutate1_20260205-205026.log
- cad-ml render may still return HTTP 422 for DXF; fallback preview generation keeps queue jobs green.
