# Stage 7 Verification Report - Preview Metadata Verification

Date: 2026-01-09

## Checks
- Migrations (tenant DB):
  - `YUANTUS_DATABASE_URL=sqlite:///yuantus_mt_skip__tenant-1__org-1.db .venv/bin/yuantus db upgrade`
- Local API (dev):
  - `PYTHONPATH=src .venv/bin/uvicorn yuantus.api.app:app --host 127.0.0.1 --port 7911`
- Preview + metadata verification:
  - `CAD_PREVIEW_ALLOW_FALLBACK=1 CAD_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/蜗杆与箱体/2004阶梯轴71.dwg" bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7911 tenant-1 org-1`
- CI regression workflow:
  - https://github.com/zensgit/yuantus-plm/actions/runs/20874796121

## Results
- PASS: `scripts/verify_cad_preview_2d.sh` completed successfully (metadata endpoints validated).
- SKIP: mesh stats endpoint returned 404 (no mesh metadata available).
- NOTE: CAD ML service not running; fallback preview path used.
- PASS: regression workflow completed successfully.
