# Relationship -> Item Migration Design (2026-01-23 20:59 +0800)

目标：在 `db-per-tenant-org` 模式下执行 Relationship -> Item 的 Phase 2 数据迁移，确保关系行可统一进入 Item 轨道。

## 范围

- tenant-1/org-1
- tenant-1/org-2
- tenant-2/org-1
- tenant-2/org-2

## 策略

- 先做全量备份（每个 tenant/org 独立库）
- 运行 dry-run 统计缺失项
- 实际迁移执行（不开启 allow-orphans）
- 记录日志与验证结果

## 关键输入

- `YUANTUS_TENANCY_MODE=db-per-tenant-org`
- `YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- `YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- `YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`

## 备份

- 目录：`tmp/rel-migration-backups-codex-yuantus-20260123_205811`

## 输出

- 验证报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_20260123_2059.md`
- 执行日志：`docs/RELATIONSHIP_ITEM_MIGRATION_20260123_205846.log`

参考设计说明：`docs/MIGRATION_RELATIONSHIP_ITEMS.md`。
