# Relationship -> Item Post-Cleanup Regression (2026-01-23 22:08 +0800)

## 环境

- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 范围：BOM Tree + Where-Used + ECO Advanced

## 执行命令

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1

DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 结果摘要

- `verify_bom_tree.sh`：`ALL CHECKS PASSED`
- `verify_where_used.sh`：`ALL CHECKS PASSED`
- `verify_eco_advanced.sh`：`ALL CHECKS PASSED`

## 日志

- `docs/VERIFY_BOM_TREE_20260123_220846.log`
- `docs/VERIFY_WHERE_USED_20260123_220846.log`
- `docs/VERIFY_ECO_ADVANCED_20260123_220846.log`
