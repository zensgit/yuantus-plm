# Relationship -> Item Migration Design (Data Case, 2026-01-23 21:39 +0800)

目标：在 `tenant-2/org-2` 中注入少量 legacy 关系数据，验证 Phase 2 迁移脚本可以把 `meta_relationships` 关系行完整迁移到 `meta_items`。

## 约束

- 使用 `db-per-tenant-org` 模式
- 只写入最小测试数据（2 条关系）
- 迁移后保留 legacy 数据，用于对比验证

## 测试数据

- Parts:
  - Part A: `LEGACY-A-1769175394` (`9ffe59c8-564a-464b-9967-6444fb375617`)
  - Part B: `LEGACY-B-1769175394` (`f125abc0-9ad1-4f41-a84e-c1567e161746`)
- Document:
  - Doc: `DOC-1769175424` (`8b547470-5d23-4ab5-aa3b-ed106b13bdd9`)
- Legacy relationships (meta_relationships):
  - Part BOM: `9efd3961-9e4f-4cbf-ae90-c2d83ca0dd62`
  - Document Part: `1985545b-666a-4bbb-9c5c-f0043de6cc06`

## 执行策略

1) 备份 tenant/org DB（已完成）
2) 手工插入 legacy 关系行（meta_relationships）
3) 执行迁移脚本（Phase 2）
4) 校验 `meta_items` 是否生成同 id 关系 Item

## 输出

- 迁移日志：`docs/RELATIONSHIP_ITEM_MIGRATION_DATA_20260123_213905.log`
- 验证报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_DATA_20260123_2139.md`
