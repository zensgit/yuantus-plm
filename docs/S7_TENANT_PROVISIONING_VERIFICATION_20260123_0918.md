# Run S7-20260123-0918 (Tenant Provisioning)

- Time: 2026-01-23 09:18:00 +0800
- Base URL: http://127.0.0.1:7910
- Mode: db-per-tenant-org
- Flags: YUANTUS_PLATFORM_ADMIN_ENABLED=true

## Command

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Result

```text
ALL CHECKS PASSED
```
