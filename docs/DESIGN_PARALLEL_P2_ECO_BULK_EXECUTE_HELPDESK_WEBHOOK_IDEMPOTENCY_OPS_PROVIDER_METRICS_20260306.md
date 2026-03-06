# 设计文档：并行支线 P2 ECO 批量执行 + Helpdesk Webhook 幂等 + Ops Provider 指标

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：
  - ECO activity 批量状态执行接口
  - Helpdesk ticket-update webhook `event_id` 幂等回放保护
  - Parallel Ops summary/Prometheus 增强 provider 维度

## 1. 目标

1. ECO 支持从批量预检查直接进入批量执行，减少调用方循环调度复杂度。
2. 防止 Helpdesk webhook 重放导致 incident/job 状态被重复覆盖。
3. 将 breakage-helpdesk provider 分布暴露到 summary/export/metrics 便于运维观测。

## 2. 方案

### 2.1 ECO 批量执行

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增 `transition_activities_bulk(...)`：

1. 先调用 `evaluate_transitions_bulk(...)` 做候选筛选。
2. 若 `truncated=true`，拒绝执行（防止部分执行歧义）。
3. 对候选活动按多轮迭代执行：
- 每轮重新 `evaluate_transition(...)`
- `can_transition=true && from!=to` 执行 `transition_activity(...)`
- `can_transition=true && from==to` 记为 `noop`
- 未执行保留为 `skipped`（区分 blocked/invalid）
4. 返回执行汇总：`executed/noop/blocked/invalid/missing/excluded`。

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `POST /eco-activities/{eco_id}/transition/bulk`

错误契约：
- 批量校验/执行错误 -> `eco_activity_transition_invalid` (400)

### 2.2 Helpdesk webhook 幂等

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

扩展 `apply_helpdesk_ticket_update(...)`：

1. 新增入参：`event_id`。
2. 读取事件历史：`provider_event_ids/provider_last_event_id`。
3. 若 `event_id` 已处理：
- 不改 incident/job
- 返回当前状态并标记 `idempotent_replay=true`
4. 新事件：
- 继续状态回写
- 记录 `provider_event_ids`（最多保留 50 条）
- 记录 `provider_last_event_id`

状态视图增强：
- `provider_last_event_id`
- `provider_event_ids_count`

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

`BreakageHelpdeskTicketUpdateRequest` 新增 `event_id`，透传到 service。

### 2.3 Ops provider 观测增强

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

1. `ParallelOpsOverviewService` 新增 `_breakage_helpdesk_summary(...)`：
- `by_provider`
- `by_provider_ticket_status`
- `providers_total`
- `with_external_ticket`
- `with_provider_ticket_status`
- `failed_jobs`

2. `summary()` 将结果挂到 `breakages.helpdesk`。
3. `prometheus_metrics()` 新增：
- `yuantus_parallel_breakage_helpdesk_jobs_total`
- `yuantus_parallel_breakage_helpdesk_failed_total`
- `yuantus_parallel_breakage_helpdesk_external_ticket_total`
- `yuantus_parallel_breakage_helpdesk_by_provider{provider=...}`
- `yuantus_parallel_breakage_helpdesk_by_provider_ticket_status{provider_ticket_status=...}`

4. `export_summary()` 的 metric rows 增加 breakages.helpdesk 维度。

## 3. 兼容性

1. 新接口为增量，不影响既有单条 transition 与 transition-check。
2. webhook 幂等字段为 payload/响应增强，无 schema 迁移。
3. summary/prometheus 为字段增强，旧消费方可忽略新增字段。

## 4. 风险与缓解

1. 风险：批量执行在依赖链场景顺序不确定。
- 缓解：多轮 reevaluate 执行，直到无进展。

2. 风险：event_id 历史无限增长。
- 缓解：事件历史固定窗口（50 条）。

3. 风险：provider 字段来源不一致。
- 缓解：统一回退链解析并写入标准化汇总。

## 5. 验收标准

1. `transition/bulk` 可在依赖链下完成批量执行并返回可解释统计。
2. 同一 `event_id` 重放不改变 incident/job 状态。
3. summary 与 prometheus 可见 provider/provider_ticket_status 维度。
4. service/router/e2e 与文档契约测试通过。
