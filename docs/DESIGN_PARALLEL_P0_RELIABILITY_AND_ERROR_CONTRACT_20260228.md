# 设计文档：并行支线 P0 可靠性与错误合同增强

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：`P0-1 + P0-2 + P0-3`

## 1. 目标

1. 提升 `doc-sync` 任务可靠性与可观测性。
2. 为 Workflow 自定义动作增加冲突治理、确定性执行、超时与重试保护。
3. 统一 `doc-sync` 与 `workflow-actions` 的 API 错误合同，降低调用方解析复杂度。

## 2. 变更概要

## 2.1 `P0-1` 文档同步可靠性

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

### 新增能力

1. 同步任务追踪字段（写入 job payload）：
- `sync_trace.trace_id`
- `sync_trace.origin_site`
- `sync_trace.payload_hash`

2. 幂等冲突诊断：
- 对同一 `dedupe_key` 的 pending/processing 任务，返回既有任务并递增 `idempotency_conflicts`。
- 记录 `idempotency_last_seen_at` 与 `idempotency_last_request`。

3. 重试预算控制：
- 支持 `metadata_json.retry_max_attempts`（范围 `1..10`）覆盖默认值。
- 传递到 `JobService.create_job(max_attempts=...)`。

4. 列表过滤与死信视图：
- `list_sync_jobs` 新增 `status/created_from/created_to` 过滤。
- `build_sync_job_view` 输出：`retry_budget`、`is_dead_letter`、`dead_letter_reason`、`sync_trace`。

### 设计取舍

- 不新增表结构，优先复用 `meta_conversion_jobs`，避免额外迁移和兼容成本。
- 死信采用“视图判定”（`failed && attempt_count>=max_attempts`）优先，满足运维观察需求并避免迁移。

## 2.2 `P0-2` Workflow 动作治理

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

### 新增能力

1. 规则参数标准化校验：
- `priority` 范围 `0..1000`
- `timeout_s` 范围 `0.01..60`
- `max_retries`（仅 `fail_strategy=retry`）范围 `1..5`

2. 冲突检测：
- 同 `target_object + workflow_map_id + from_state + to_state + trigger_phase` 视为同 scope。
- 将冲突摘要写入 `action_params.conflict_scope`（count/rule_ids）。

3. 确定性执行顺序：
- 规则匹配后按 `(priority, name, id)` 固定排序。

4. 超时与重试保护：
- 每条规则执行按 `timeout_s` 判定超时。
- `retry` 策略按 `1 + max_retries` 上限执行。

5. 标准结果码：
- `OK`
- `WARN`
- `BLOCK`
- `RETRY_EXHAUSTED`

结果码写入 `WorkflowCustomActionRun.result.result_code`，并附带 `execution` 元数据（order/priority/timeout_s/max_retries）。

### 设计取舍

- 不新增字段，结果码与治理信息写入 `result/action_params`，最大化与现有 schema 兼容。
- 维持 `run.status` 既有语义（`completed/warning/failed`），避免影响已有逻辑分支。

## 2.3 `P0-3` 错误合同统一

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

### 新增能力

1. 统一错误结构：
- `detail.code`
- `detail.message`
- `detail.context`

2. 新增工具函数：
- `_error_detail`
- `_raise_api_error`
- `_parse_utc_datetime`

3. 覆盖接口：
- `doc-sync`（site upsert/health/create/list/get/replay）
- `workflow-actions`（rule upsert / execute）

### 错误码约定（本次新增）

- `remote_site_not_found`
- `remote_site_inactive`
- `doc_sync_job_invalid`
- `doc_sync_filter_invalid`
- `doc_sync_job_not_found`
- `doc_sync_replay_failed`
- `invalid_datetime`
- `invalid_workflow_rule`
- `workflow_action_execution_failed`

## 3. API 返回增强

1. `GET /api/v1/doc-sync/jobs`
- 新 query：`status`、`created_from`、`created_to`
- 新字段：`sync_trace`、`retry_budget`、`is_dead_letter`、`dead_letter_reason`

2. `GET /api/v1/doc-sync/jobs/{job_id}`
- 返回结构统一为 `build_sync_job_view`。

3. `POST /api/v1/workflow-actions/rules`
- 返回新增：`execution_priority`、`timeout_s`、`max_retries`、`conflict_count`

4. `GET /api/v1/workflow-actions/rules`
- 列表项新增上述治理字段。

5. `POST /api/v1/workflow-actions/execute`
- 每个 run 新增 `result_code`。

## 4. 风险与回滚

1. 风险：旧规则 `action_params` 格式不规范。
- 处理：服务层增加容错默认值。

2. 风险：客户端依赖旧错误字符串。
- 处理：保留 `detail.message` 语义与原文本一致，新增结构化 `code/context`。

3. 回滚策略：
- 单文件回滚可按 `parallel_tasks_service.py` / `parallel_tasks_router.py` 分离。
- 变更未引入迁移，回滚成本低。

