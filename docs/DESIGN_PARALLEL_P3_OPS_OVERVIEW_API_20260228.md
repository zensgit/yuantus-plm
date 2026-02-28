# 设计文档：并行支线 P3（Parallel Ops Overview API）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：并行支线运行指标统一总览（doc-sync/workflow/breakage/consumption/overlay）

## 1. 目标

1. 提供单一 API 汇总并行支线关键运行指标，降低值班排障成本。
2. 统一输出窗口统计（1/7/14/30/90 天）与基础 SLO 提示。
3. 在不新增迁移的前提下，复用现有模型与服务数据。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增 `ParallelOpsOverviewService`：

1. 参数标准化
- `window_days` 只允许：`1, 7, 14, 30, 90`。
- 非法值抛 `ValueError`。

2. 聚合分区
- `doc_sync`：从 `meta_conversion_jobs` 过滤 `task_type like document_sync_%`，统计状态分布、dead-letter 比率、成功率、平均尝试次数。
- `workflow_actions`：从 `meta_workflow_custom_action_runs` 统计状态、结果码（`result_code`）、失败率。
- `breakages`：从 `meta_breakage_incidents` 统计状态、严重度、责任归属、开放率、重复异常率。
- `consumption_templates`：从 `meta_consumption_plans.properties.template` 统计模板版本数、活动版本一致性。
- `overlay_cache`：复用 `ThreeDOverlayService.cache_stats()` 补充命中率。

3. SLO 提示（`slo_hints`）
- `overlay_cache_hit_rate_low`
- `doc_sync_dead_letter_rate_high`
- `workflow_action_failed_rate_high`
- `breakage_open_rate_high`

## 2.2 API 层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `GET /api/v1/parallel-ops/summary`

查询参数：
- `window_days`（默认 7）
- `site_id`（可选）
- `target_object`（可选）
- `template_key`（可选）

错误合同：
- `parallel_ops_invalid_request`

## 3. 数据与兼容性

1. 不新增数据库表/迁移。
2. 仅新增读 API，不改变现有写路径。
3. 与现有并行支线接口兼容，不影响主流程。

## 4. 风险与回滚

1. 风险：聚合逻辑在大窗口下查询量上升。
- 缓解：窗口离散化 + 按需过滤参数。

2. 风险：overlay 缓存统计是进程内维度，不是全局值。
- 缓解：响应中保留语义，面向单实例运维使用。

3. 回滚：
- 下线 `parallel-ops/summary` 路由即可；无 schema 回滚要求。

## 5. 验收标准

1. API 输出包含五类指标分区与统一时间窗口。
2. 非法 `window_days` 返回结构化错误合同。
3. 服务与路由测试覆盖成功路径和异常路径。
