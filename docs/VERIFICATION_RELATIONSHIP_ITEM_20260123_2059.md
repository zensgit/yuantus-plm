# Relationship -> Item Migration Verification (2026-01-23 20:59 +0800)

## 环境

- 模式：`db-per-tenant-org`
- 数据库：Postgres
- 租户/组织：tenant-1/org-1, tenant-1/org-2, tenant-2/org-1, tenant-2/org-2

## 备份

- `tmp/rel-migration-backups-codex-yuantus-20260123_205811/`

## Dry Run

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --dry-run
```

Dry-run 结果（节选）：

```text
Relationships: total=0 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 0
```

## Actual Run

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --update-item-types
```

实际执行结果（节选）：

```text
Relationships: total=0 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 0
```

## 结论

- 所有 tenant/org 库中 `meta_relationships` 为空，本次迁移未写入数据。
- 迁移脚本执行成功，无缺失 type/source/related。
- 详细日志：`docs/RELATIONSHIP_ITEM_MIGRATION_20260123_205846.log`
