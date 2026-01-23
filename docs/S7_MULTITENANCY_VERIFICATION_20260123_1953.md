# S7 多租户深度验证报告（2026-01-23 19:54 +0800）

## 环境

- 模式：`db-per-tenant-org`
- 基地址：`http://127.0.0.1:7910`
- 关键开关：
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 数据库：
  - `YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`

## 执行命令

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

## 结果摘要

- `verify_multitenancy.sh`：`ALL CHECKS PASSED`
- `verify_quotas.sh`：`ALL CHECKS PASSED`
- `verify_audit_logs.sh`：`ALL CHECKS PASSED`
- `verify_ops_health.sh`：`ALL CHECKS PASSED`
- `verify_search_reindex.sh`：`ALL CHECKS PASSED`
- `verify_tenant_provisioning.sh`：`ALL CHECKS PASSED`

## 原始日志

- `docs/S7_MULTITENANCY_VERIFICATION_20260123_1953.log`
