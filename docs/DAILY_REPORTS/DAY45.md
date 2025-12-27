# Day 45 - BOM Compare compare_mode

## Scope
- Add compare_mode support (only_product/summarized/num_qty/by_position/by_reference).
- Extend line_key options for config-based alignment.
- Update verification to cover compare_mode behavior.

## Verification

Command:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
BOM Compare: OK
BOM Compare only_product: OK
BOM Compare num_qty: OK
ALL CHECKS PASSED
```
