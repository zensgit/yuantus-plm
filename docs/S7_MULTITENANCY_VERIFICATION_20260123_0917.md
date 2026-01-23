# Run S7-20260123-0917 (Ops Hardening / Multi-Tenancy Deep)

- Time: 2026-01-23 09:17:00 +0800
- Base URL: http://127.0.0.1:7910
- Mode: db-per-tenant-org
- Flags: YUANTUS_QUOTA_MODE=enforce, YUANTUS_AUDIT_ENABLED=true, YUANTUS_PLATFORM_ADMIN_ENABLED=true

## Command

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

## Result

```text
ALL CHECKS PASSED
```
