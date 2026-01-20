# S7 多租户深度验证报告

## 环境

- 模式：`db-per-tenant-org`
- 服务：Postgres + MinIO + API + Worker + CAD Extractor
- 关键开关：
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`
- 辅助变量：
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `VERIFY_QUOTA_MONITORING=1`
  - `VERIFY_RETENTION=1`
  - `VERIFY_RETENTION_ENDPOINTS=1`

## 关键命令

```bash
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

## 结果摘要

- `verify_multitenancy.sh`：`ALL CHECKS PASSED`
- `verify_quotas.sh`：`ALL CHECKS PASSED`
- `verify_audit_logs.sh`：`ALL CHECKS PASSED`
- `verify_ops_health.sh`：`ALL CHECKS PASSED`
- `verify_search_reindex.sh`：`ALL CHECKS PASSED`

## Run S7-20260120-0833（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-20 08:33:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## 结论

S7 深度验证已完成：多租户隔离、配额限制、审计留存、健康检查与索引回归在 `db-per-tenant-org` 模式下均通过。
