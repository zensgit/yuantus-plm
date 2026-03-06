# 设计文档：并行支线 P2 ECO 状态机 + Helpdesk 双向回写

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：
  - ECO Activity transition 规则强化（状态别名、状态机、预检查接口）
  - Breakage/Helpdesk ticket 状态双向回写（provider ticket -> incident + sync job）

## 1. 目标

1. ECO 活动流转具备明确状态机约束，避免非法跳转和隐式状态分叉。
2. 提供 transition-check 预检查能力，支持前端/流程引擎在执行前获得可跳转决策。
3. Helpdesk 外部工单状态更新可回写 Breakage incident 状态、责任人与同步任务状态。
4. 统一 provider 状态语义，保留 provider 原始上下文字段，提升审计与排障能力。

## 2. 方案

### 2.1 ECO 状态机强化

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

1. 新增状态别名归一化：
- `draft -> pending`
- `in_progress/eco -> active`
- `done -> completed`
- `cancel/cancelled -> canceled`

2. 增加显式 `_TRANSITIONS` 状态迁移矩阵，封装 `evaluate_transition(...)`：
- 返回 `from_status/to_status/allowed_targets/can_transition/reason_code/blockers`。
- 统一阻塞依赖校验（`blocking_dependencies`）。

3. `transition_activity(...)` 复用 `evaluate_transition(...)` 决策，避免重复逻辑。

4. reopen 语义：从终态迁移回非终态时，清理 `closed_at/closed_by_id`。

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

1. 新增接口：
- `GET /eco-activities/activity/{activity_id}/transition-check?to_status=...`

2. 错误契约：
- not found -> `eco_activity_not_found` (404)
- invalid transition/status -> `eco_activity_transition_invalid` (400)

### 2.2 Helpdesk 双向回写

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

1. 新增 provider ticket 状态别名与映射：
- provider status -> incident status
- provider status -> sync status (`queued/in_progress/completed/failed`)

2. 扩展 helpdesk job 状态视图字段：
- `provider_ticket_status`
- `provider_ticket_updated_at`
- `provider_assignee`
- `provider_payload`

3. 新增 `apply_helpdesk_ticket_update(...)`：
- 解析/归一化 provider ticket status
- 更新 incident（status/responsibility/updated_at）
- 回写 job payload (`helpdesk_sync/result`)
- 推导并更新 job status（`processing/completed/failed`）

4. provider 回退策略：
- 优先请求参数 provider
- 回退 `helpdesk_sync.provider`
- 回退 `integration.provider`
- 回退 payload provider

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

1. 新增接口：
- `POST /breakages/{incident_id}/helpdesk-sync/ticket-update`

2. 入参支持：
- `provider_ticket_status`
- `provider_updated_at`（ISO-8601，统一经 `_parse_utc_datetime` 转 UTC-naive）
- `provider_assignee/provider_payload`
- `incident_status/incident_responsibility`

3. 错误契约：
- incident not found -> `breakage_not_found` (404)
- 其他业务校验 -> `breakage_helpdesk_sync_invalid` (400)
- 时间格式错误 -> `invalid_datetime` (400)

## 3. 兼容性

1. 新接口为增量，不影响既有 `execute/result/status` 路径。
2. `get_helpdesk_sync_status(...)` 新增字段为返回增强，向后兼容。
3. 无数据库 schema 变更。

## 4. 风险与缓解

1. 风险：provider 状态语义不一致导致 incident 状态偏差。
- 缓解：集中别名 + 映射表，默认回退 `open/queued`，并保留 `provider_payload` 便于审计。

2. 风险：状态机过严导致历史调用失败。
- 缓解：对常见历史别名（`done/in_progress/draft`）提供兼容映射。

3. 风险：外部 webhook 时间格式不稳定。
- 缓解：统一 ISO-8601 解析器并返回 `invalid_datetime` 合同错误。

## 5. 验收标准

1. ECO transition-check 在阻塞依赖与可跳转场景下返回可解释决策。
2. ECO transition 支持别名且遵循状态机。
3. ticket-update 能驱动 incident 与 sync job 联动更新。
4. provider 回写字段在 status 接口可见。
5. 受影响 service/router/e2e 测试通过。
