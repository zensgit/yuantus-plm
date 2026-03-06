# 设计文档：并行支线 P2 Doc Sync Ops Closure

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：在既有 `doc-sync` 能力上补齐运维闭环（死信视图、批量重放、摘要导出）。

## 1. 目标

1. 让值班人员可以快速识别死信任务并定位重试对象。
2. 支持按站点/窗口批量重放，减少手工单条 replay 成本。
3. 统一产出 `json/csv/md` 摘要导出，满足日常巡检与周报。

## 2. 方案

## 2.1 服务层

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

在 `DocumentMultiSiteService` 新增：

1. `list_dead_letter_sync_jobs(...)`
- 支持 `site_id/window_days/limit` 过滤。
- 死信判断规则：
  - payload 显式 dead_letter 标识，或
  - `status=failed` 且 `attempt_count >= max_attempts`。

2. `replay_sync_jobs_batch(...)`
- 支持两种入口：
  - 指定 `job_ids`；
  - 按 `site_id + window_days` 自动选取 failed/dead-letter。
- 返回结构化批处理结果：`requested/replayed/failed/failures/replayed_jobs`。

3. `export_sync_summary(...)`
- 基于 `sync_summary` 复用查询逻辑。
- 支持 `json/csv/md`：
  - `json`：完整 summary payload；
  - `csv`：overall + per-site 扁平行；
  - `md`：值班摘要 + 站点表格。

4. 参数归一化
- `_normalize_sync_limit(limit)`：统一限制 `1..500`。

## 2.2 路由层

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：

1. `GET /api/v1/doc-sync/jobs/dead-letter`
- 返回 dead-letter 任务列表与 `operator_id`。

2. `POST /api/v1/doc-sync/jobs/replay-batch`
- 请求体：`SyncReplayBatchRequest`。
- 返回批量 replay 执行结果与 `operator_id`。

3. `GET /api/v1/doc-sync/summary/export`
- 参数：`site_id/window_days/export_format`。
- 返回 `StreamingResponse`，带 `Content-Disposition` 与 `X-Operator-Id`。

错误合同：
- `doc_sync_dead_letter_invalid`
- `doc_sync_replay_batch_invalid`
- `doc_sync_summary_export_invalid`

## 3. 兼容性

1. 无数据库迁移。
2. 不改变既有 `/doc-sync/summary` 与 `/doc-sync/jobs/{id}` 行为。
3. 新增接口为读/重放能力，保持向后兼容。

## 4. 风险与缓解

1. 风险：批量 replay 可能对下游站点造成突发流量。
2. 缓解：限制 `limit<=500`，并保留 dead-letter-only 默认策略。
3. 风险：导出格式字段后续演进可能影响下游脚本。
4. 缓解：字段采用追加策略，不删除既有列。

## 5. 验收标准

1. 死信列表接口按站点/窗口可正确筛选。
2. 批量 replay 具备幂等去重与失败明细输出。
3. 摘要导出 `json/csv/md` 三格式可用。
4. 服务层、路由层、E2E 均有覆盖测试。
