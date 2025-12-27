# Day 54 Report

Date: 2025-12-26

## Scope
- Fix CAD real samples script and re-run validation.

## Work Completed
- Adjusted docker compose port probe to avoid `set -e` early exit in `verify_cad_real_samples.sh`.
- Re-ran real CAD samples validation with explicit DB/S3/CAD extractor settings.

## Verification

Command:
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
CAD_EXTRACTOR_BASE_URL=http://localhost:8200 \
CAD_ML_BASE_URL=http://localhost:8001 \
bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_cad_real_samples_rerun.log
```

Results:
- ALL CHECKS PASSED

Artifacts:
- docs/VERIFICATION_RESULTS.md (Run CAD-REAL-2)
- /tmp/verify_cad_real_samples_rerun.log
