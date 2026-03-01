# 设计文档：并行支线 P1-2 Breakage Metrics BOM 行维度分组扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 参考：`/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main/addons/plm_breakages/models/mrp_bom.py`
- 范围：为 breakage 分组统计补充 `bom_line_item_id` 维度，以对齐 BOM 断裂定位视角。

## 1. 目标

1. 扩展 `breakages/metrics/groups` 支持 BOM 行粒度聚合。
2. 扩展 `breakages/metrics/groups/export` 同步支持 BOM 行维度导出。
3. 保持现有错误合同与分页行为不变。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

改动：
1. 在 `_group_by_fields` 中新增映射：
- `bom_line_item_id -> bom_line_item_id`
2. 复用现有 `metrics_groups(...)` 与 `export_metrics_groups(...)` 逻辑，无需新增分支逻辑。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

改动：
1. 更新 `group_by` 参数描述，新增 `bom_line_item_id`。
2. 查询与导出两个路由保持同一维度说明，减少接口歧义。

## 3. 兼容性

1. 仅新增分组枚举值，不影响已有维度。
2. 不涉及数据库迁移与历史数据变更。

## 4. 风险与回滚

1. 风险
- 若 `bom_line_item_id` 缺失，分组结果可能为空。

2. 缓解
- 延续现有“空值跳过”策略；导出仍返回结构化空行。

3. 回滚
- 移除 `_group_by_fields` 中 `bom_line_item_id` 条目及对应测试即可。

## 5. 验收标准

1. `group_by=bom_line_item_id` 查询返回正确聚合。
2. `group_by=bom_line_item_id` 导出（json/csv/md）可用。
3. service/router/e2e 回归通过。
