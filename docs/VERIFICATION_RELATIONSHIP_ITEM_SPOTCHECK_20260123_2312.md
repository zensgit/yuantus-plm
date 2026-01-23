# Relationship Migration Spot Check (2026-01-23 23:12 +0800)

## 范围

- BOM Tree
- ECO Impact + BOM Diff + Batch Approvals

## 执行命令

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1

DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 结果摘要

- `verify_bom_tree.sh`：`ALL CHECKS PASSED`
- `verify_eco_advanced.sh`：`ALL CHECKS PASSED`

## 日志

- `docs/VERIFY_SPOT_BOM_WHERE_20260123_231242.log`
- `docs/VERIFY_SPOT_ECO_ADV_20260123_231242.log`
