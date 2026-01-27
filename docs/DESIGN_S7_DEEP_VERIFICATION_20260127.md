# S7 多租户深度验证设计（2026-01-27）

## 目标
在 **db-per-tenant-org** 模式下完成 S7 深度验证，覆盖：
- 多租户隔离
- 配额（org/user/file/job）
- 审计日志
- 运维健康检查
- 搜索重建
- 租户开通（Platform Admin）

## 验证顺序
1. `verify_multitenancy.sh`
2. `verify_quotas.sh`
3. `verify_audit_logs.sh`
4. `verify_ops_health.sh`
5. `verify_search_reindex.sh`
6. `verify_tenant_provisioning.sh`

脚本总入口：`scripts/verify_s7.sh`

## 前置条件
- API 运行在 `db-per-tenant-org` 模式。
- 若要验证租户开通，需启用平台管理员：
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- CLI 需与 API 使用**同一套数据库**（尤其在 API 运行于 Docker 时）。

## 参考环境（宿主机 CLI 指向 Docker Postgres）
```bash
export MODE=db-per-tenant-org
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
```

## 执行命令
```bash
RUN_TENANT_PROVISIONING=1 \
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

## 产出
- 验证报告：`docs/VERIFICATION_S7_DEEP_20260127_2.md`
