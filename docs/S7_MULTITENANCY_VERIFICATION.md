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

## Run S7-20260120-2226（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-20 22:26:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 备注：未启用审计留存验证（`VERIFY_RETENTION=0`）
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=0 \
VERIFY_RETENTION_ENDPOINTS=0 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2258（Audit Retention + Endpoints）

- 时间：`2026-01-20 22:58:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_AUDIT_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2259（Tenant Provisioning）

- 时间：`2026-01-20 22:59:57 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2317（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-20 23:17:38 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2317（Tenant Provisioning）

- 时间：`2026-01-20 23:17:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## 结论

S7 深度验证已完成：多租户隔离、配额限制、审计日志、健康检查与索引回归在 `db-per-tenant-org` 模式下均通过。

## Run S7-20260121-103449（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-21 10:34:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过
- 详细记录：`docs/S7_MULTITENANCY_VERIFICATION_20260121_103449.md`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
VERIFY_QUOTA_MONITORING=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260121-110044（Tenant Provisioning）

- 时间：`2026-01-21 11:00:44 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 日志：`docs/S7_TENANT_PROVISIONING_20260121_110044.log`
- 结果：全部通过
- 详细记录：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260121_110044.md`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
PLATFORM_TENANT=platform \
PLATFORM_ORG=platform \
PLATFORM_USER=platform-admin \
PLATFORM_PASSWORD=platform-admin \
PLATFORM_USER_ID=9001 \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-0917（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-23 09:17:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 详细记录：`docs/S7_MULTITENANCY_VERIFICATION_20260123_0917.md`

执行命令：

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

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-0918（Tenant Provisioning）

- 时间：`2026-01-23 09:18:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 详细记录：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260123_0918.md`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-1107（S7 Deep Verification）

- 时间：`2026-01-23 11:07:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 脚本：`scripts/verify_s7.sh`
- 详细记录：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1107.md`
- 结果：全部通过

执行命令：

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
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-1107（Tenant Provisioning）

- 时间：`2026-01-23 11:07:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 脚本：`scripts/verify_s7.sh`
- 详细记录：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260123_1107.md`
- 结果：全部通过

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## 追加结论

S7 多租户深度验证与平台管理员租户开通均通过（db-per-tenant-org）。
