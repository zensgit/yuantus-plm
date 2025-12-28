# Day 47 - Compare Mode Summarized + ECO Export Metadata

## Scope
- Add summarized compare_mode coverage in BOM compare verification.
- Include compare_mode/line_key metadata in ECO export.
- Re-verify ECO advanced flow with compare_mode export check.

## Verification

Commands:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
BOM Compare summarized: OK
Impact export files: OK
ALL CHECKS PASSED
```
