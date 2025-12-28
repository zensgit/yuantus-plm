# Day 37 - Full Regression

## Scope
- Run full regression suite after CAD parsing updates.

## Verification - verify_all.sh

Command:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 33  FAIL: 0  SKIP: 5
ALL TESTS PASSED
```

Notes:
- Skipped: CAD Auto Part / CAD Extractor Stub / CAD Extractor External / CAD Extractor Service / Tenant Provisioning
