# 设计文档：并行支线 P2 Breakage Helpdesk Failure Replay Trends Export + Cleanup Dry-Run

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`

## 1. 目标

1. 为 replay trends 增加导出能力（json/csv/md），支撑值班与周报直接复用。
2. 为 replay cleanup 增加 `dry_run`，降低线上清理操作风险。
3. 在不破坏现有 replay 查询与告警链路的前提下，增强可运维性与变更安全性。

## 2. 范围

- Service
  - `export_breakage_helpdesk_replay_trends(...)`
  - `cleanup_breakage_helpdesk_failure_replay_batches(..., dry_run: bool=False)`
- Router
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends/export`
  - `POST /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup`（请求体新增 `dry_run`）
- Tests
  - service/router/e2e 增补 replay trends export 与 cleanup dry_run 合同验证

## 3. 设计细节

### 3.1 Replay trends export

- 输入：`window_days/bucket_days/provider/job_status/sync_status/export_format`
- 输出格式：
  - `json`：完整 trends payload
  - `csv`：`bucket_start,bucket_end,total_jobs,failed_jobs,failed_rate,batches_total`
  - `md`：趋势表格摘要
- 错误合同：`export_format` 非法返回 `parallel_ops_invalid_request`

### 3.2 Cleanup dry_run

- `dry_run=true`：
  - 仅扫描并返回将被归档的 job/batch 列表
  - 不写入 `metadata.replay.archived`
- `dry_run=false`：
  - 执行现有归档写入逻辑
- 返回新增字段：`dry_run`

## 4. 风险与兼容

1. 新增导出接口是增量路径，不影响旧接口。
2. `dry_run` 默认 `false` 保持向后兼容；值班可显式先 dry-run 再执行。
3. 导出基于 trends 结果二次序列化，不引入新的口径分歧。

## 5. 验收标准

1. replay trends export 的 `json/csv/md` 均可下载。
2. cleanup dry-run 不会实际归档 replay batch。
3. service/router/e2e 对新增能力验证通过。
