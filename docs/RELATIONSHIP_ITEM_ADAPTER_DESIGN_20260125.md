# Relationship Item Adapter Design (2026-01-25)

## 背景

现有架构以 Item 关系（meta_items.source_id/related_id）承载 BOM/ECO 等核心链路。
RelationshipType 与 meta_relationships 保留为兼容层，但写入已被禁用。
本阶段目标是确保运行时查询/创建路径优先使用 ItemType.is_relationship，
仅在必要时回退到 RelationshipType（legacy）。

## 目标

- 优先使用 ItemType.is_relationship 解析关系类型
- RelationshipType 仅作为 legacy fallback，并给出警告
- 保持现有 API 行为不变

## 变更点

- RelationshipService
  - 关系解析顺序改为 ItemType 优先
  - RelationshipType 作为 fallback，并记录 deprecation warning

- QueryService
  - expand 关系解析顺序改为 ItemType 优先
  - RelationshipType fallback 时记录 deprecation warning

## 兼容性

- 若 legacy RelationshipType 存在，但 ItemType 尚未创建，将自动补齐
- ItemType 已存在但非 relationship：
  - 若存在 RelationshipType，将被修正为 relationship
  - 否则抛出错误，提示类型不正确

## 风险与回滚

- 风险：低（逻辑顺序调整，保留 legacy fallback）
- 回滚：恢复 RelationshipType 优先解析逻辑即可
