# Verification: CAD Preview 2D (20260121)

## Goal
Validate CAD 2D preview using cad-ml-api (port 8000) with render fallback enabled.

## Result
PASS (ALL CHECKS PASSED).

## Command
```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
CAD_ML_BASE_URL=http://localhost:8000 \
scripts/verify_cad_preview_2d.sh
```

## Key Output
- Uploaded file_id: 630a312a-628f-40b7-b5cc-5f317536aa5e
- Preview endpoint HTTP 302.
- Mesh stats unavailable (available=false).

## Notes
- cad-ml-api render endpoint uses CAD_RENDER_FALLBACK_URL to forward DWG rendering to the local CAD render service.
- cad-ml health: http://localhost:8000/api/v1/vision/health = 200.
