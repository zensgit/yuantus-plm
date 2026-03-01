# 设计文档：并行支线 P1-2 Breakage Metrics BOM 行过滤扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 参考：`/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main/addons/plm_breakages/models/mrp_bom.py`
- 范围：为 breakage 指标、分组与导出接口增加 `bom_line_item_id` 过滤参数，支持按 BOM 行定位异常。

## 1. 目标

1. 支持 `breakages/metrics` 按 BOM 行过滤。
2. 支持 `breakages/metrics/groups` 按 BOM 行过滤。
3. 支持 `breakages/metrics/export` 与 `breakages/metrics/groups/export` 在导出中透传 BOM 行过滤上下文。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

改动：
1. `_apply_incident_filters(...)` 新增 `bom_line_item_id` 过滤条件。
2. `metrics(...)` / `metrics_groups(...)` / `export_metrics(...)` / `export_metrics_groups(...)` 全链路新增 `bom_line_item_id` 参数并透传。
3. 导出行新增 `bom_line_item_id_filter` 字段：
- breakage metrics CSV/JSON/MD 过滤上下文同步可见。
- groups export CSV/JSON/MD 过滤上下文同步可见。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

改动：
1. 以下接口新增 query 参数 `bom_line_item_id`：
- `GET /api/v1/breakages/metrics`
- `GET /api/v1/breakages/metrics/groups`
- `GET /api/v1/breakages/metrics/export`
- `GET /api/v1/breakages/metrics/groups/export`
2. 错误合同 `breakage_metrics_invalid_request` 的 `context` 中新增 `bom_line_item_id`。

## 3. 兼容性

1. 参数为可选，默认不改变历史查询行为。
2. 无数据库结构变更，无迁移需求。

## 4. 风险与回滚

1. 风险
- 新增参数可能导致部分调用方遗漏更新导出解析字段。

2. 缓解
- 仅新增字段，不删除旧字段；旧解析逻辑仍可工作。
- 通过 service/router/e2e 回归覆盖过滤参数透传。

3. 回滚
- 回滚服务参数与路由 query 参数即可，无数据回滚步骤。

## 5. 验收标准

1. 四个 breakage 指标接口均接受 `bom_line_item_id`。
2. 查询结果 `filters` 正确回显 BOM 行过滤值。
3. CSV/MD/JSON 导出包含 `bom_line_item_id_filter` 上下文字段。
4. 目标与全量回归通过。
