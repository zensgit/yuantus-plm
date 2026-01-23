# Relationship -> Item Migration Verification (Data Case, 2026-01-23 21:39 +0800)

## 环境

- 模式：`db-per-tenant-org`
- 基地址：`http://127.0.0.1:7910`
- 目标租户/组织：`tenant-2/org-2`

## 测试数据

- Part A: `LEGACY-A-1769175394` (`9ffe59c8-564a-464b-9967-6444fb375617`)
- Part B: `LEGACY-B-1769175394` (`f125abc0-9ad1-4f41-a84e-c1567e161746`)
- Document: `DOC-1769175424` (`8b547470-5d23-4ab5-aa3b-ed106b13bdd9`)
- Legacy relationships:
  - Part BOM: `9efd3961-9e4f-4cbf-ae90-c2d83ca0dd62`
  - Document Part: `1985545b-666a-4bbb-9c5c-f0043de6cc06`

## 迁移命令

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --update-item-types
```

输出（节选）：

```text
Relationships: total=2 existing_items=0
Missing type=0 source=0 related=0
Created ItemType for relationship: Document Part
Migrated relationship items: 2
```

## 验证

- `meta_relationships` 行数：`2`
- `meta_items` 中同 id 行数：`2`
- 关系 Item 映射：
  - `Part BOM` -> ItemType `Part BOM`
  - `Document Part` -> ItemType `Document Part`

## 日志

- `docs/RELATIONSHIP_ITEM_MIGRATION_DATA_20260123_213905.log`

## 清理（可选）

```sql
DELETE FROM meta_items WHERE id IN (
  '9efd3961-9e4f-4cbf-ae90-c2d83ca0dd62',
  '1985545b-666a-4bbb-9c5c-f0043de6cc06'
);
DELETE FROM meta_relationships WHERE id IN (
  '9efd3961-9e4f-4cbf-ae90-c2d83ca0dd62',
  '1985545b-666a-4bbb-9c5c-f0043de6cc06'
);
DELETE FROM meta_items WHERE id IN (
  '9ffe59c8-564a-464b-9967-6444fb375617',
  'f125abc0-9ad1-4f41-a84e-c1567e161746',
  '8b547470-5d23-4ab5-aa3b-ed106b13bdd9'
);
```
