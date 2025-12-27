# Day 16 - Full Regression (MT + Audit Enabled)

## Scope
- Run full regression suite in db-per-tenant-org mode with audit logs enabled.
- Restore single-tenant docker compose after verification.

## Verification

Command:

```bash
AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 19  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```
