# Day 39 - Platform Admin + External Extractor Samples

## Scope
- Enable platform admin and verify tenant provisioning.
- Verify external extractor with real DWG/STEP/PRT samples.

## Verification - Tenant Provisioning

Command:

```bash
YUANTUS_PLATFORM_ADMIN_ENABLED=true docker compose up -d --force-recreate api

export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

## Verification - External Extractor Samples

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
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export YUANTUS_AUTH_MODE=required

CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg' \
  CAD_EXTRACTOR_CAD_FORMAT='AUTOCAD' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1

CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg' \
  CAD_EXTRACTOR_CAD_FORMAT='AUTOCAD' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1

CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp' \
  CAD_EXTRACTOR_CAD_FORMAT='STEP' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1

CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt' \
  CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```
