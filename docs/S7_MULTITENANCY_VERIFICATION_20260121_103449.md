# S7 多租户深度验证报告（20260121_103449）

## 环境
- API: http://127.0.0.1:7910
- Tenancy: db-per-tenant-org
- Schema mode: create_all
- Audit: enabled + retention endpoints
- Quota: enforce
- 运行容器：`docker-compose.yml` + `docker-compose.mt.yml`

## 关键参数
- TENANT/ORG: tenant-1/org-1, tenant-2/org-2
- DB URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
- DB URL template: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}
- Identity DB: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg
- Retention: days=1, max_rows=10, prune_interval=1

## 执行命令
```bash
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

## 结果汇总
- Multi-tenancy：tenant/org 隔离通过（A1/A2/B1）
- Quotas：org/user/file/job quota 阻断通过，平台管理员 quota monitoring OK
- Audit：/admin/audit 查询通过，retention + endpoints（retention/prune）通过
- Ops health：/health、/health/deps OK（db/identity/storage 正常）
- Search reindex：reindex indexed=66；search 命中新增 item；清理完成

## 关键记录
- Search reindex 创建的 Part ID：`149a0093-e449-4a58-8f72-fc4c60801a11`
- Search engine：db

## 结论
S7 多租户深度验证全量通过（Ops Hardening 组合脚本）。

## 备注
- 本次未单独执行 `verify_tenant_provisioning.sh`；若需要平台管理员租户开通验证，可追加执行。
