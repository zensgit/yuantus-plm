# Relationship → Item Migration (Phase 2)

目标：把 `meta_relationships` 的历史数据迁移到 `meta_items`，让 ECO/BOM/Effectivity/版本链统一使用 “关系即 Item” 的模型。

## 映射规则

- `meta_relationships.id` → `meta_items.id`
- `meta_relationships.relationship_type_id` → `meta_item_types.id`（取 `meta_relationship_types.name`）
- `meta_relationships.source_id` → `meta_items.source_id`
- `meta_relationships.related_id` → `meta_items.related_id`
- `meta_relationships.properties` → `meta_items.properties`
- `meta_relationships.sort_order` → `meta_items.properties.sort_order`（若未存在）
- `meta_relationships.state` → `meta_items.state`（缺省为 `Active`）
- `meta_relationships.created_by_id` → `meta_items.created_by_id`
- `meta_items.config_id` 使用 `meta_relationships.id`（保证稳定、非空）

## 预检（建议）

在每个目标 DB 内执行：

```sql
-- 关系行数
SELECT COUNT(*) FROM meta_relationships;

-- 缺失关系类型
SELECT COUNT(*)
FROM meta_relationships r
LEFT JOIN meta_relationship_types t ON t.id = r.relationship_type_id
WHERE t.id IS NULL;

-- 缺失 source / related
SELECT COUNT(*)
FROM meta_relationships r
LEFT JOIN meta_items s ON s.id = r.source_id
WHERE s.id IS NULL;

SELECT COUNT(*)
FROM meta_relationships r
LEFT JOIN meta_items s ON s.id = r.related_id
WHERE s.id IS NULL;
```

## 执行方式

脚本：`scripts/migrate_relationship_items.py`

单库：

```bash
python scripts/migrate_relationship_items.py
```

db-per-tenant：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant \
python scripts/migrate_relationship_items.py --tenant tenant-1
```

db-per-tenant-org：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1
```

可选参数：

- `--dry-run`：只统计，不写入
- `--allow-orphans`：跳过缺失 type/source/related 的行
- `--update-item-types`：修补既有 ItemType 的关系属性

## 回滚

该迁移只写入 `meta_items`，回滚方式：

```sql
DELETE FROM meta_items
WHERE id IN (SELECT id FROM meta_relationships);
```

## 风险与建议

- 缺失 source/related：建议先修复数据，否则迁移会失败或跳过。
- 关系类型缺失：需补齐 `meta_relationship_types`。
- 若已有重复 id（`meta_items.id` 与 `meta_relationships.id` 冲突），脚本会跳过已存在的行。
- 若 tenant/org 数据库尚未初始化（无 `meta_relationships` 表），脚本会记录并跳过；如需迁移请先初始化 schema。

## Phase 3（非破坏性清理）

- 保留 `meta_relationships` 表，只读兼容层不删除。
- 移除/禁用遗留写入路径（已将 `PartBOMBridge` 标记为 deprecated 并禁用）。
- 兼容层写入阻断为硬开启（无环境变量开关）。
- `RelationshipType` 仅作为 legacy 兼容可选种子；默认不再创建。
  - 如需保留旧集成，设置 `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED=true`
- 管理员报告：`GET /api/v1/admin/relationship-types/legacy-usage` 用于追踪 legacy 关系依赖。
- 生产环境不要开启任何模拟或迁移测试开关。
