# 设计文档：并行支线 P2 Breakage Helpdesk Failure Triage + Replay + Export Ops

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 参考：`references/odoo18-enterprise-main/addons/plm_breakages`、`references/odoo18-enterprise-main/addons/plm_ent_breakages_helpdesk`

## 1. 目标

1. 补齐 helpdesk 失败工单 triage 的“分析 + 批量落库 + replay 入队”闭环能力。
2. 增强 failures export 作业的运营可观测能力（jobs overview）。
3. 引入 provider 级失败预算告警与指标，降低单 provider 异常被全局指标掩盖的风险。
4. 维持既有错误合同与兼容性，确保值班平台平滑接入。
5. 增补 replay 批次状态查询与 export jobs 概览高级聚合，支撑并行值班排障。

## 2. 范围

- Service (`ParallelOpsOverviewService`)
  - `breakage_helpdesk_failure_triage(...)`
  - `apply_breakage_helpdesk_failure_triage(...)`
  - `enqueue_breakage_helpdesk_failure_replay_jobs(...)`
  - `get_breakage_helpdesk_failure_replay_batch(...)`
  - `breakage_helpdesk_failures_export_jobs_overview(...)`
  - `enqueue/execute/get/run/download/cleanup` for export jobs
  - `summary(...)` / `alerts(...)` / `prometheus_metrics(...)` / `export_summary(...)` provider 阈值扩展
- Router
  - `POST /api/v1/parallel-ops/breakage-helpdesk/failures/replay/enqueue`
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}`
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/overview`
  - `summary/alerts/summary-export/metrics` 新增 provider `warn+critical` 阈值 query 透传
- Worker
  - 复用既有 `breakage_helpdesk_sync_stub` 消费 replay 入队结果
- Tests
  - service/router/e2e + 受影响全量回归

## 3. 设计要点

### 3.1 Triage + Replay

- triage 仍以失败 job 为目标对象，支持 `job_ids` 与筛选条件两种模式。
- replay 入队策略：
  - 仅对失败 job 生效；
  - 自动继承 incident/provider/integration；
  - 写入 replay metadata（`batch_id/source_job_id/requested_by_id/requested_at/replay_index`）；
  - 使用新的 replay idempotency key，避免与原始 job dedupe 冲突。
- replay 批次状态查询：
  - 按 `batch_id` 聚合同批 replay job；
  - 输出 `by_job_status/by_sync_status/by_provider/by_failure_category`；
  - 提供分页列表（含 `source_job_id`、状态、重放索引与时间戳）。

### 3.2 Export Jobs Overview

- 新增概览接口用于值班看板聚合：
  - 过滤维度：`window_days/provider/failure_category/export_format/page/page_size`
  - 聚合维度：`by_job_status/by_sync_status/by_provider/by_failure_category/by_export_format`
  - 输出执行耗时统计：`count/min/max/avg/p50/p95`
  - 输出最近作业列表（含下载可用状态、failure_category、duration_seconds）

### 3.3 Provider 失败预算

- 新增阈值：
  - `breakage_helpdesk_provider_failed_rate_warn`
  - `breakage_helpdesk_provider_failed_min_jobs_warn`
  - `breakage_helpdesk_provider_failed_rate_critical`
  - `breakage_helpdesk_provider_failed_min_jobs_critical`
- `summary` 新增 provider 级失败聚合：
  - `by_provider_failed`
  - `provider_failed_rates.{provider}.{total_jobs,failed_jobs,failed_rate}`
- 告警策略：
  - 当 `provider_total_jobs >= min_jobs_critical` 且 `failed_rate > rate_critical` 时发出
    `breakage_helpdesk_provider_failed_rate_critical`（`level=critical`）；
  - 当 `provider_total_jobs >= min_jobs` 且 `failed_rate > rate_warn` 时发出
    `breakage_helpdesk_provider_failed_rate_high`（`level=warn`）。
- 新增 Prometheus 指标：
  - `yuantus_parallel_breakage_helpdesk_provider_failed_total{provider=...}`
  - `yuantus_parallel_breakage_helpdesk_provider_failed_rate{provider=...}`

### 3.4 错误合同

- replay/overview 参数错误：`parallel_ops_invalid_request`
- 导出作业生命周期错误：`parallel_ops_export_job_invalid` / `parallel_ops_export_job_not_found`

## 4. 兼容性与风险

1. 增量接口与增量字段，不破坏旧调用路径。
2. replay 误触发风险由 `limit + filters + job_ids` 约束。
3. provider 告警新增后，若阈值配置过敏可能产生告警放大，需要按环境调参。
4. replay batch 查询基于任务表扫描，若历史数据量很大可后续补充按时间窗口或索引优化。

## 5. 验收标准

1. replay 入队接口可创建新的 helpdesk sync job，并写入 replay 元信息。
2. replay batch 查询接口可按 `batch_id` 返回聚合与分页明细。
3. export jobs overview 可返回聚合 + 列表 + 耗时统计，支持 provider/failure_category/export_format 过滤。
4. provider 级失败预算可在 `summary/alerts/metrics/export_summary` 生效（含 warn/critical 双阈值）。
5. service/router/e2e 与受影响回归通过。
