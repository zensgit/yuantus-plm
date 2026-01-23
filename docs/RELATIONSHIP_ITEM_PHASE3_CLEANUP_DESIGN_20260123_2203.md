# Relationship -> Item Phase 3 Cleanup Design (2026-01-23 22:03 +0800)

目标：彻底禁用 legacy `meta_relationships` 写入路径，确保兼容层只读不可被环境变量关闭。

## 变更点

- 写入阻断不再依赖环境变量，始终为只读模式。
- 保留兼容层与监控端点（relationship-writes）。

## 验证策略

- 通过 ORM 直接插入 `meta_relationships`，应被写入阻断并抛错。

## 输出

- 日志：`docs/RELATIONSHIP_ITEM_PHASE3_CLEANUP_20260123_220359.log`
- 验证报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_CLEANUP_20260123_2203.md`
