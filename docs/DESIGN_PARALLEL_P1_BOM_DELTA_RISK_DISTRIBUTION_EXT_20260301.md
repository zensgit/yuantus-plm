# 设计文档：并行支线 P1-1 BOM Delta 风险分级聚合扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：为 BOM delta 预览摘要补齐风险分级聚合，支持快速评审与导出解读。

## 1. 目标

1. 在 delta 摘要中提供操作级风险分布（而不只给单一 `risk_level`）。
2. 保持对现有 preview/export 接口兼容，仅追加字段。
3. 提升结构性变更（add/remove）在风险统计中的可解释性。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/bom_service.py`

增强 `build_delta_preview(...)`：

1. 结构性操作风险标记
- `add/remove` 操作新增 `risk_level="medium"`。

2. 新增 `risk_distribution` 聚合
- 统计桶：`critical/high/medium/low/none`
- 统计来源：所有 `operations` 的 `risk_level`
- 追加到：
  - `summary.risk_distribution`
  - `change_summary.risk_distribution`

## 2.2 兼容性

1. 原有字段保持不变：`summary.risk_level`、`change_summary.severity` 等。
2. CSV 导出沿用既有字段，不引入破坏性变更。
3. 不涉及数据库迁移。

## 3. 风险与回滚

1. 风险
- 下游若对操作级 `risk_level` 为空有强依赖，`add/remove` 将从空值变为 `medium`。

2. 缓解
- 仅在预览语义层追加解释，未改变 API 路径与关键字段含义。

3. 回滚
- 回滚 `bom_service.build_delta_preview` 和对应测试即可。

## 4. 验收标准

1. `summary/change_summary` 均包含 `risk_distribution`。
2. `add/remove` 操作带 `risk_level=medium`。
3. 现有 BOM delta 测试与全量回归通过。
