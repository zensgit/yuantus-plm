# Relationship -> Item Actual Migration (2026-01-23 22:41 +0800)

## 目标

- tenant/org: `tenant-2/org-2`
- 模式：`db-per-tenant-org`

## 备份

- 目录：`tmp/rel-migration-backups-codex-yuantus-20260123_224120`
- 文件：`yuantus_mt_pg__tenant-2__org-2-codex-yuantus-20260123_224120.sql`

> 说明：宿主机无 `pg_dump`，使用 `docker exec yuantus-postgres-1 pg_dump ...` 完成备份。

## 迁移命令

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --update-item-types
```

## 结果摘要

- `Relationships: total=0`
- `Missing type/source/related = 0`
- `Migrated relationship items: 0`

## 日志

- `docs/RELATIONSHIP_ITEM_MIGRATION_ACTUAL_20260123_224147.log`
