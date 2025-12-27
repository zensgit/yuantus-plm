# Day 57 Report

Date: 2025-12-26

## Scope
- Validate real DWG samples with Haochen/Zhongwang connectors.

## Work Completed
- Added `verify_cad_connectors_real_2d.sh` with optional real-sample paths and dedupe-safe upload.
- Integrated optional stage into `verify_all.sh` (`RUN_CAD_REAL_CONNECTORS_2D=1`).
- Documented the new verification flow.

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
CAD_REAL_FORCE_UNIQUE=1 \
bash scripts/verify_cad_connectors_real_2d.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_cad_connectors_real_2d.log
```

Results:
- ALL CHECKS PASSED

Artifacts:
- docs/VERIFICATION_RESULTS.md (Run S5-B-Real-2D-1)
- /tmp/verify_cad_connectors_real_2d.log
