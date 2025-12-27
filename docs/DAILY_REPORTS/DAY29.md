# Day 29 - Audit + Multi-Tenancy Regression

## Scope
- Enable audit logs and db-per-tenant-org mode.
- Bootstrap tenant databases and run migrations.
- Run full regression suite to clear SKIPs.

## Verification

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_AUDIT_ENABLED=true \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 24  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

Notes:
- Document: 58cce8b0-f1cc-4f5d-80e6-f31d293d7b6c
