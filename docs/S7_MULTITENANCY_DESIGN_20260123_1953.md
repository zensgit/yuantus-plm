# S7 多租户深度验证设计说明（2026-01-23 19:54 +0800）

目标：在 `db-per-tenant-org` 模式下完成多租户隔离、配额、审计、健康检查、索引回归与平台管理员租户开通的联测，确保私有化交付具备最小运营能力。

## 范围

- 多租户隔离（tenant/org 维度）
- 配额（Quota）强制执行
- 审计日志 + 留存/清理
- 健康检查（/health、/health/deps）
- 搜索重建（/search/reindex）
- 平台管理员租户/组织开通

## 环境与关键开关

- 运行模式：`db-per-tenant-org`
- 关键开关：
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`

## 验证入口

- 统一入口：`scripts/verify_s7.sh`
- 子脚本：
  - `scripts/verify_ops_hardening.sh`
  - `scripts/verify_multitenancy.sh`
  - `scripts/verify_quotas.sh`
  - `scripts/verify_audit_logs.sh`
  - `scripts/verify_ops_health.sh`
  - `scripts/verify_search_reindex.sh`
  - `scripts/verify_tenant_provisioning.sh`

## 输出

- 验证报告：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1953.md`
- 执行日志：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1953.log`
- 汇总追加：`docs/S7_MULTITENANCY_VERIFICATION.md`、`docs/VERIFICATION_RESULTS.md`

备注：详细设计与机制说明参考 `docs/S7_MULTITENANCY_DESIGN.md`。
