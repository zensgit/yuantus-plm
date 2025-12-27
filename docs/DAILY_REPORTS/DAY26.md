# Day 26 - Audit + Multi-Tenancy Regression

## Scope
- Enable audit logs and db-per-tenant-org mode.
- Bootstrap tenant databases and run migrations.
- Run full regression to close all SKIP items.

## Verification

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_AUDIT_ENABLED=true \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 23  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```
