# CAD-ML Quick Regression Report (2026-02-05)

## Command
```
CAD_PREVIEW_SAMPLE_FILE="$CAD_PREVIEW_SAMPLE_FILE" \
RUN_CAD_ML_DOCKER=1 \
YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" \
scripts/verify_cad_ml_quick.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Inputs
- BASE_URL: http://127.0.0.1:7910
- TENANT/ORG: tenant-1 / org-1
- CAD_PREVIEW_SAMPLE_FILE (escaped JSON):
  "/Users/huazhou/Downloads/\u8bad\u7ec3\u56fe\u7eb8/\u8bad\u7ec3\u56fe\u7eb8/ACAD-\u5e03\u5c40\u7a7a\u767d DXF-2013.dxf"
- CAD_ML_BASE_URL: http://127.0.0.1:18000

## Summary
- CAD 2D Preview: PASS
- CAD OCR Title Block: PASS

## Notes
- Full log: /tmp/verify_cad_ml_quick_20260205-115334.log
- cadquery not installed warnings occurred during CAD conversions but did not fail verification.
- Initial cad-ml health probe saw connection reset before succeeding.
