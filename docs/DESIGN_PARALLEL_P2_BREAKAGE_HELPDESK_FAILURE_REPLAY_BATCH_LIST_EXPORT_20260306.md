# 设计文档：并行支线 P2 Breakage Helpdesk Failure Replay Batch List + Export + Replay Metrics

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：`ParallelOpsOverviewService` + `parallel_tasks_router` + 受影响 tests/e2e

## 1. 目标

1. 为 replay 批次提供运营视角的批量查询接口，支持按 provider / job_status / sync_status 过滤。
2. 为 replay 批次提供可下载导出（json/csv/md），便于值班复盘与外部协同。
3. 将 replay 指标并入 `summary`、`metrics`、`summary/export`，降低“仅能看到失败，不可见重放闭环”的观测盲区。
4. 保持错误合同清晰：参数错误统一 `parallel_ops_invalid_request`，批次不存在返回 `parallel_ops_replay_batch_not_found`。

## 2. 设计范围

- Service：`src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - 新增 `_collect_breakage_helpdesk_replay_rows(...)` 作为 replay 数据收敛层。
  - 新增 `list_breakage_helpdesk_failure_replay_batches(...)`。
  - 新增 `export_breakage_helpdesk_failure_replay_batch(...)`。
  - `get_breakage_helpdesk_failure_replay_batch(...)` 重用 collector，避免重复筛选逻辑。
  - `summary()/prometheus_metrics()/summary export` 新增 replay 聚合字段。
- Router：`src/yuantus/meta_engine/web/parallel_tasks_router.py`
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches`
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}/export`
- Tests：service/router/e2e 扩展 replay 批次列表、导出与指标断言。

## 3. 关键结构

### 3.1 Replay rows collector

- 输入过滤：`since`、`batch_id_filter`、`provider_filter`、`job_status_filter`、`sync_status_filter`。
- 识别 replay 任务：依赖 `job.metadata.replay.batch_id`。
- 规范输出：统一 `batch_id/source_job_id/replay_index/provider/job_status/sync_status/failure_category` 等字段。
- 内部统计字段：`_created_at_dt/_requested_at_dt/_duration_seconds` 仅用于排序与统计。

### 3.2 Replay 批次列表

- 分页：`page/page_size`。
- 批次聚合：
  - `by_job_status`
  - `by_sync_status`
  - `by_provider`
  - `by_failure_category`
  - `duration_seconds`（`count/min/max/avg/p50/p95`）
- 全局聚合：`total_batches/total_jobs` + `by_*` 汇总。

### 3.3 Replay 批次导出

- 格式：`json|csv|md`。
- 数据源：collector + `batch_id_filter`。
- 合同：
  - 不支持格式 -> `ValueError("unsupported export_format")`
  - 批次不存在 -> `ValueError("replay batch not found")`

### 3.4 Replay 观测增强

- `summary.breakages.helpdesk` 新增：
  - `replay_jobs_total`
  - `replay_batches_total`
  - `replay_failed_jobs`
  - `replay_failed_rate`
  - `replay_by_job_status`
  - `replay_by_provider`
- Prometheus 新增：
  - `yuantus_parallel_breakage_helpdesk_replay_jobs_total`
  - `yuantus_parallel_breakage_helpdesk_replay_batches_total`
  - `yuantus_parallel_breakage_helpdesk_replay_failed_total`
  - `yuantus_parallel_breakage_helpdesk_replay_failed_rate`
  - `yuantus_parallel_breakage_helpdesk_replay_by_provider{provider=...}`
- `summary/export` 新增 replay 行，保证报表与 API 字段一致。

## 4. 风险与兼容

1. replay 数据来自任务表扫描，历史数据量大时可能产生查询开销；当前通过窗口过滤与分页控制风险。
2. 批次导出与批次查询共享 collector，减少口径漂移风险。
3. 接口为新增路径，旧调用不受影响。

## 5. 验收标准

1. replay 批次列表可返回分页批次、聚合计数与耗时统计。
2. replay 批次导出支持 `json/csv/md` 且下载头正确。
3. `summary/metrics/summary export` 可见 replay 指标。
4. service/router/e2e 定向测试通过。
