# Relationship -> Item Phase 2 Design (2026-01-24 00:51 +0800)

目标：当 `meta_relationship_types` 不存在或不完整时，关系查询/创建仍能完全依赖 `ItemType.is_relationship` 正常运行。

## 范围

- `RelationshipService` 解析关系类型时支持 `ItemType` 回退。
- `AMLQueryService` expand 解析关系类型时支持 `ItemType` 回退。

## 方案

1) 解析优先级：
   - 先查 `RelationshipType`（兼容存量数据）。
   - 未命中则查 `ItemType.id/label` 且必须 `is_relationship=True`。

2) 关系创建校验：
   - 优先使用 `RelationshipType` 的 source/related 定义。
   - 若无 `RelationshipType`，使用 `ItemType.source_item_type_id` / `related_item_type_id`。

3) 关系查询 expand：
   - 使用 `ItemType.id` 作为 `item_type_id` 过滤条件。

## 非目标

- 数据迁移（由迁移脚本处理）。
- 移除 `RelationshipType` 表或 API（Phase 3+ 再做）。

## 输出

- 验证脚本：`scripts/verify_relationship_itemtype_expand.sh`
- 验证报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE2_20260124_0051.md`
