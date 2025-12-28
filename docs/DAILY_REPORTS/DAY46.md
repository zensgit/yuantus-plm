# Day 46 - ECO Impact compare_mode

## Scope
- Add compare_mode support to ECO impact and BOM diff endpoints.
- Extend ECO advanced verification to cover compare_mode.

## Verification

Command:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
BOM diff: OK
BOM diff only_product: OK
Impact analysis: OK
Impact export files: OK
Batch approvals (admin): OK
Batch approvals (viewer denied): OK
ALL CHECKS PASSED
```
