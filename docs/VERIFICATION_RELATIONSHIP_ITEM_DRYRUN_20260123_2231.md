# Relationship -> Item Dry-Run (2026-01-23 22:31 +0800)

## 环境

- 模式：`db-per-tenant-org`
- 目标：`tenant-2/org-2`
- 数据库：Postgres

## 执行命令

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --dry-run
```

## 结果摘要

- `Relationships: total=0`
- `Missing type/source/related = 0`
- `Migrated relationship items: 0`

## 日志

- `docs/RELATIONSHIP_ITEM_DRYRUN_20260123_223124.log`
