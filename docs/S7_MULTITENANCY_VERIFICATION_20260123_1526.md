# Run S7-20260123-1526 (S7 Deep Verification)

- Time: 2026-01-23 15:26:28 +0800
- Base URL: http://127.0.0.1:7910
- Mode: db-per-tenant-org
- Flags: YUANTUS_QUOTA_MODE=enforce, YUANTUS_AUDIT_ENABLED=true, YUANTUS_PLATFORM_ADMIN_ENABLED=true
- Script: scripts/verify_s7.sh (wrapper)

## Command

```bash
CLI=/Users/huazhou/Downloads/Github/YuantusPLM/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/YuantusPLM/.venv/bin/python \
MODE=db-per-tenant-org \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

## Result

```text
ALL CHECKS PASSED
```
