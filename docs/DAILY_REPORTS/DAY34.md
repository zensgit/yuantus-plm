# Day 34 - OCR Field Expansion + Filename Fallback

## Scope
- Extend OCR title block extraction with revision/weight.
- Add filename fallback for drawing_no to align with part_number.

## Verification - CAD OCR Title Block

Command:

```bash
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- OCR keys detected: drawing_no
