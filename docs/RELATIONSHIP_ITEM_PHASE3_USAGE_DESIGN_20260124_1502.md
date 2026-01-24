# Relationship -> Item Phase 3 Usage Report Design (2026-01-24 15:02 +0800)

目标：提供管理员可见的 legacy `RelationshipType` 使用情况报告，用于评估遗留依赖并决定清理节奏。

## 范围

- 新增管理员端点：
  - `GET /api/v1/admin/relationship-types/legacy-usage`
- 输出统计：
  - legacy `RelationshipType` 行数
  - legacy `meta_relationships` 行数
  - 关系 ItemType 数量
  - 关系 Item 行数（meta_items 中 is_relationship）
  - 可选 per-RelationshipType 细分（include_details）

## 行为

- 默认只返回汇总统计（`include_details=false`）
- db-per-tenant-org 模式下必须指定 `org_id`
- 当 legacy 表不存在时，返回 `meta_relationships_missing=true` 或 `meta_relationship_types_missing=true`
- 对存在 legacy 依赖的情况返回 `warnings`

## 非目标

- 自动修复或迁移数据
- 去除 legacy 表（仅报告）

## 关联配置

- `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED` 仍然控制 legacy 类型是否播种
