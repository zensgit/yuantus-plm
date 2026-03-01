# 设计文档：并行支线 P1-2 Breakage Metrics 多维聚合扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：在 `breakages/metrics` 与导出能力上补齐按产品/批次/责任维度聚合输出。

## 1. 目标

1. 完成 Backlog 中 P1-2 的多维聚合要求（产品/批次/责任）。
2. 让 API 看板与导出结果共享同一统计口径。
3. 保持现有接口兼容，不引入迁移。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

增强 `BreakageIncidentService.metrics(...)`：

1. 新增聚合字段
- `by_product_item`
- `by_batch_code`
- `top_product_items`（Top 10）
- `top_batch_codes`（Top 10）

2. 统计规则
- 仅统计非空 `product_item_id` / `batch_code`。
- 维持既有 `by_responsibility`、`hotspot_components`、`trend` 不变。

3. 导出联动
- `export_metrics(..., export_format=md)` 增加上述维度摘要，确保导出与面板一致。

## 2.2 API 层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

- 复用现有 `GET /api/v1/breakages/metrics`，无需新增参数。
- 返回体新增多维聚合字段（向后兼容，旧字段不变）。

## 3. 风险与回滚

1. 风险
- 返回体字段增加后，强 schema 客户端若做严格白名单校验，需同步兼容。

2. 缓解
- 保持旧字段和语义不变，仅追加新字段。

3. 回滚
- 回滚服务层新增聚合字段与测试即可；无 schema 回滚要求。

## 4. 验收标准

1. `breakages/metrics` 返回产品与批次维度聚合。
2. `top_product_items/top_batch_codes` 排序稳定（按计数降序）。
3. 导出 markdown 含多维聚合摘要。
4. service/router/e2e 测试覆盖新增字段。
