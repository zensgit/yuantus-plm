# Relationship -> Item Phase 3 Seeder Design (2026-01-24 14:29 +0800)

目标：默认只播种 `ItemType.is_relationship`，将 `RelationshipType` 降级为可选 legacy 兼容层。

## 设计要点

- 默认行为：
  - 仅创建 `ItemType`（例如 `Part BOM`），用于“关系即 Item”主路径。
  - 不再自动创建 `meta_relationship_types`。
- 兼容开关：
  - 环境变量 `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED=true` 时才播种 legacy `RelationshipType`。
- 无 API 变化：
  - 关系创建/查询继续优先 `ItemType`，在存在 `RelationshipType` 时兼容读取。

## 范围

- `MetaSchemaSeeder` 仅影响 `RelationshipType` 是否创建。
- 迁移脚本与运行时读写逻辑不变。

## 非目标

- 移除 `RelationshipType` 表（保持只读兼容）。
- 删除 `meta_relationships` 表。

## 关联配置

- `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED`（默认 `false`）
