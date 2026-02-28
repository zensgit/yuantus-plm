# 设计文档：并行支线 P3（Parallel Ops Overview + Trends + Alerts + Summary Export + Failure Details + Prometheus）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：并行支线运行指标统一总览（doc-sync/workflow/breakage/consumption/overlay）

## 1. 目标

1. 提供单一 API 汇总并行支线关键运行指标，降低值班排障成本。
2. 统一输出窗口统计（1/7/14/30/90 天）与基础 SLO 提示。
3. 提供失败明细分页接口、告警视图与 Prometheus 采集接口，便于看板和告警系统接入。
4. 提供 JSON/CSV/Markdown 总览导出，便于日报与归档场景。
5. 提供时间桶趋势 API，用于值班看板观察指标变化轨迹。
4. 在不新增迁移的前提下，复用现有模型与服务数据。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增/增强 `ParallelOpsOverviewService`：

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

4. 失败明细分页能力
- `doc_sync_failures(window_days, site_id, page, page_size)`
- `workflow_failures(window_days, target_object, page, page_size)`
- 分页统一输出：`pagination.page/page_size/pages/total`

5. 趋势能力
- `trends(window_days, bucket_days, site_id, target_object, template_key)`
- `bucket_days` 允许：`1|7|14|30`，且必须 `<= window_days`
- 输出：按 bucket 的 `doc_sync/workflow_actions/breakages` 计数与比率，附带聚合 totals。

6. 告警视图
- `alerts(window_days, site_id, target_object, template_key, level)`
- 从 `summary.slo_hints` 生成告警聚合：`status/total/by_code/hints`
- `level` 允许：`warn|critical|info`

7. Summary 导出
- `export_summary(window_days, site_id, target_object, template_key, export_format)`
- `export_format` 允许：`json|csv|md`
- 输出内容 + `media_type` + `filename`，由路由层统一下载响应。

8. Prometheus 文本导出
- `prometheus_metrics(window_days, site_id, target_object, template_key)`
- 输出 `text/plain; version=0.0.4` 格式，指标覆盖：
  - doc-sync 总量/状态分布/成功率/dead-letter
  - workflow 总量/失败率/result_code 分布
  - breakage 总量/开放量
  - consumption template 版本总量
  - overlay cache 请求量/命中率
  - slo hints 总量

## 2.2 API 层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `GET /api/v1/parallel-ops/summary`
- `GET /api/v1/parallel-ops/trends`
- `GET /api/v1/parallel-ops/alerts`
- `GET /api/v1/parallel-ops/summary/export`
- `GET /api/v1/parallel-ops/doc-sync/failures`
- `GET /api/v1/parallel-ops/workflow/failures`
- `GET /api/v1/parallel-ops/metrics`

查询参数：
- `window_days`（默认 7）
- `site_id`（可选）
- `target_object`（可选）
- `template_key`（可选）
- `bucket_days`（仅 trends，默认 `1`）
- `level`（仅 alerts，可选）
- `export_format`（仅 summary/export，默认 `json`）

错误合同：
- `parallel_ops_invalid_request`

## 3. 数据与兼容性

1. 不新增数据库表/迁移。
2. 仅新增读 API，不改变现有写路径。
3. 与现有并行支线接口兼容，不影响主流程。

## 4. 风险与回滚

1. 风险：聚合与失败明细在大窗口下查询量上升。
- 缓解：窗口离散化 + 按需过滤参数。

2. 风险：overlay 缓存统计是进程内维度，不是全局值。
- 缓解：响应中保留语义，面向单实例运维使用。

3. 回滚：
- 下线 `parallel-ops/*` 新增路由即可；无 schema 回滚要求。

## 5. 验收标准

1. API 输出包含五类指标分区与统一时间窗口。
2. 非法 `window_days` 返回结构化错误合同。
3. 服务与路由测试覆盖成功路径和异常路径。
4. `alerts` 支持等级筛选并输出按 code 聚合。
5. `summary/export` 支持 `json/csv/md`，非法格式返回结构化错误合同。
6. `trends` 支持按 bucket 输出时序点，非法 `bucket_days` 返回结构化错误合同。
