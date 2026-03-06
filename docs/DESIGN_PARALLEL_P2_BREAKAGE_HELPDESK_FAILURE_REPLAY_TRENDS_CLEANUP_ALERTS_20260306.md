# 设计文档：并行支线 P2 Breakage Helpdesk Failure Replay Trends + Cleanup + Replay Alerts

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 适用范围：`ParallelOpsOverviewService` + `parallel_tasks_router` + tests/e2e

## 1. 目标

1. 为 replay 批次补齐趋势视图，支持值班按时间窗快速判断 replay 是否收敛。
2. 增加 replay 批次 TTL 清理能力，避免 replay 运维视图长期堆积历史批次。
3. 将 replay 风险纳入 `summary/alerts/metrics/export` 阈值体系，形成统一告警口径。

## 2. 设计范围

- Service
  - `breakage_helpdesk_replay_trends(...)`
  - `cleanup_breakage_helpdesk_failure_replay_batches(...)`
  - `summary()/alerts()/prometheus_metrics()/export_summary()` replay 阈值扩展
  - `_collect_breakage_helpdesk_replay_rows(...)` 支持 archived 过滤
- Router
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends`
  - `POST /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup`
  - `summary/alerts/summary-export/metrics` replay 阈值 query 透传
- Tests
  - service/router/e2e 覆盖 replay trends + cleanup + replay SLO hints

## 3. 核心方案

### 3.1 Replay 趋势

- 输入过滤：`window_days/bucket_days/provider/job_status/sync_status`
- 输出：
  - `points[]`：`total_jobs/failed_jobs/failed_rate/batches_total/by_provider/by_job_status/by_sync_status`
  - `aggregates`：`total_jobs/failed_jobs/failed_rate/total_batches`
  - 全局维度聚合：`by_provider/by_job_status/by_sync_status`

### 3.2 Replay 批次 TTL 清理

- 输入：`ttl_hours/limit`
- 清理策略：
  - 仅处理到达 TTL 的 replay job（`created_at <= cutoff`）
  - 仅处理终态（`completed|failed|cancelled`）
  - 软归档：写入 `metadata.replay.archived=true` + `archived_at/archive_reason/archive_ttl_hours`
- 清理后行为：
  - replay collector 默认排除 archived 数据
  - replay list/get/export/trends 默认不返回归档批次

### 3.3 Replay 告警阈值

新增阈值：
- `breakage_helpdesk_replay_failed_rate_warn`
- `breakage_helpdesk_replay_failed_total_warn`
- `breakage_helpdesk_replay_pending_total_warn`

新增 hints：
- `breakage_helpdesk_replay_failed_rate_high`
- `breakage_helpdesk_replay_failed_total_high`
- `breakage_helpdesk_replay_pending_total_high`

新增 summary 字段：
- `replay_pending_jobs`
- `replay_by_sync_status`

新增 Prometheus 指标：
- `yuantus_parallel_breakage_helpdesk_replay_pending_total`

## 4. 兼容性与风险

1. 新增接口与新增字段为增量能力，不影响既有调用。
2. 采用软归档，不删除 job 主记录，保留审计可追溯性。
3. cleanup 仅处理终态 replay job，避免误清理在途任务。

## 5. 验收标准

1. replay trends 可返回窗口聚合与时间桶细分。
2. replay cleanup 可归档过期 replay 批次并在 list/trends 中消失。
3. replay 阈值可在 summary/alerts/metrics/export 生效。
4. service/router/e2e 回归通过。
