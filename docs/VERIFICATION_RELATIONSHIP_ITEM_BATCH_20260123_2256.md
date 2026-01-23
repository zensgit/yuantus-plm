# Relationship -> Item Batch Migration (2026-01-23 22:56 +0800)

## 目标

- tenant-1/org-1
- tenant-1/org-2
- tenant-2/org-1

## 备份

- 目录：`tmp/rel-migration-backups-codex-yuantus-20260123_225618`
- 文件：
  - `yuantus_mt_pg__tenant-1__org-1-codex-yuantus-20260123_225618.sql`
  - `yuantus_mt_pg__tenant-1__org-2-codex-yuantus-20260123_225618.sql`
  - `yuantus_mt_pg__tenant-2__org-1-codex-yuantus-20260123_225618.sql`

## 执行命令（示例）

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg   .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --dry-run

YUANTUS_TENANCY_MODE=db-per-tenant-org YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg   .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --update-item-types
```

## 结果摘要

- `tenant-1/org-1`：Relationships total=0, migrated=0
- `tenant-1/org-2`：Relationships total=0, migrated=0
- `tenant-2/org-1`：Relationships total=0, migrated=0

## 日志

- `docs/RELATIONSHIP_ITEM_DRYRUN_tenant-1_org-1_20260123_225638.log`
- `docs/RELATIONSHIP_ITEM_ACTUAL_tenant-1_org-1_20260123_225638.log`
- `docs/RELATIONSHIP_ITEM_DRYRUN_tenant-1_org-2_20260123_225638.log`
- `docs/RELATIONSHIP_ITEM_ACTUAL_tenant-1_org-2_20260123_225638.log`
- `docs/RELATIONSHIP_ITEM_DRYRUN_tenant-2_org-1_20260123_225638.log`
- `docs/RELATIONSHIP_ITEM_ACTUAL_tenant-2_org-1_20260123_225638.log`
