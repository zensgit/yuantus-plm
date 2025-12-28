# Day 15 - Audit Logs + Multi-Tenancy Verification

## Scope
- Enable audit logs with retention and verify /admin/audit behavior.
- Switch to db-per-tenant-org mode and verify tenant/org isolation.
- Restore single-tenant docker compose after verification.

## Verification

Command:

```bash
AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Command:

```bash
YUANTUS_SCHEMA_MODE=create_all \
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

Result:

```text
ALL CHECKS PASSED
```
