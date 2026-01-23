# Relationship -> Item Phase 3 Design (2026-01-23 21:55 +0800)

目标：验证 legacy `meta_relationships` 写入已被阻断且可监控，确保系统只读兼容层生效。

## 范围

- 平台管理员端点：
  - `GET /api/v1/admin/relationship-writes`
  - `POST /api/v1/admin/relationship-writes/simulate`
- 监控逻辑：写入阻断计数 + warn_threshold 触发

## 前置条件

- `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- `tenant_id=platform` 下存在平台管理员用户
- 服务运行在 `db-per-tenant-org`（本次执行环境）

## 验证策略

1) 查询阻断计数（初始值）
2) 调用 simulate 触发阻断计数
3) 再次查询并检查 `blocked`/`warn` 是否变化

## 输出

- 日志：`docs/RELATIONSHIP_WRITE_BLOCKS_20260123_215530.log`
- 验证报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_20260123_2155.md`
