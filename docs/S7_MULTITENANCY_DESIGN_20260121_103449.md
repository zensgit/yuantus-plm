# S7 多租户深度验证设计（20260121_103449）

目标：在 `db-per-tenant-org` 模式下完成多租户隔离 + 配额 + 审计 + 健康 + 索引回归验证，确保私有化交付具备最小 SaaS 运维能力。

## 范围
- 多租户隔离（tenant/org 不串库、不串数据）
- 配额（enforce 模式：org/user/file/job）
- 审计（含 retention + endpoints）
- 健康检查（/health, /health/deps）
- 搜索索引回归（reindex + query）

## 环境
- Docker Compose: `docker-compose.yml` + `docker-compose.mt.yml`
- 数据库：Postgres（宿主机 55432）
- 存储：MinIO（宿主机 59000/59001）
- API：`http://127.0.0.1:7910`

## 关键配置
- `YUANTUS_TENANCY_MODE=db-per-tenant-org`
- `YUANTUS_SCHEMA_MODE=create_all`
- `YUANTUS_QUOTA_MODE=enforce`
- `YUANTUS_AUDIT_ENABLED=true`
- `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- `YUANTUS_AUDIT_RETENTION_DAYS=1`
- `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
- `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`

## 设计要点
1. 多租户数据库模板：`yuantus_mt_pg__{tenant_id}__{org_id}`
2. CLI 与 API 同库：通过 `YUANTUS_DATABASE_URL*`/`YUANTUS_IDENTITY_DATABASE_URL` 指向宿主机 Postgres 端口。
3. 验证顺序：`verify_multitenancy` → `verify_quotas` → `verify_audit_logs` → `verify_ops_health` → `verify_search_reindex`。
4. Retention 验证：启用 `AUDIT_RETENTION_*` 与 retention endpoints。

## 验证命令
```bash
# 启动多租户容器
YUANTUS_QUOTA_MODE=enforce \
YUANTUS_AUDIT_ENABLED=true \
YUANTUS_AUDIT_RETENTION_DAYS=1 \
YUANTUS_AUDIT_RETENTION_MAX_ROWS=10 \
YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
YUANTUS_PLATFORM_ADMIN_ENABLED=true \
docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build

# S7 深度验证
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
VERIFY_QUOTA_MONITORING=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```
