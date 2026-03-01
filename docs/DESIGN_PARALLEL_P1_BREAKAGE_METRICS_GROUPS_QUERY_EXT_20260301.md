# 设计文档：并行支线 P1-2 Breakage Metrics 分组查询扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：新增可分页的 breakage 多维分组查询接口，补齐“按产品/批次/责任组织维度聚合查询”能力。

## 1. 目标

1. 从“返回聚合字典”升级到“可分页分组结果”，支持看板与运营查询直接复用。
2. 支持三种分组维度：`product_item_id`、`batch_code`、`responsibility`。
3. 与现有 breakage 指标错误合同统一，保持接口可观测与可回放。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增能力：

1. `metrics_groups(...)`
- 参数：
  - `group_by`（`product_item_id|batch_code|responsibility`）
  - 过滤参数复用 `metrics(...)`
  - `page/page_size` 分页
- 输出：
  - `group_by`
  - `total_groups`
  - `groups[]`（`group_value/count`）
  - `pagination`
  - `filters`

2. 规范化方法
- `_normalize_group_by(...)`：非法维度抛 `ValueError`。

3. 排序策略
- 使用 `Counter.most_common()`，按计数降序输出。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `GET /api/v1/breakages/metrics/groups`

请求参数：
- `group_by`（默认 `responsibility`）
- `status/severity/product_item_id/batch_code/responsibility`
- `trend_window_days`（7/14/30 校验沿用）
- `page/page_size`

错误合同：
- `breakage_metrics_invalid_request`
- `context` 包含 `group_by` 与分页/过滤参数。

## 3. 兼容性

1. 新增只读接口，不影响现有 `breakages/metrics` 与 `breakages/metrics/export`。
2. 不涉及数据库迁移。

## 4. 风险与回滚

1. 风险
- 当维度值很多时，分组统计返回量大。

2. 缓解
- 强制分页（`page_size` 上限 200）。

3. 回滚
- 下线 `/breakages/metrics/groups` 与对应 service 方法；无 schema 回滚要求。

## 5. 验收标准

1. 三个分组维度均可查询。
2. 分组结果支持分页，排序稳定。
3. 非法 `group_by` 返回结构化错误合同。
4. service/router/e2e 测试覆盖成功与失败路径。
