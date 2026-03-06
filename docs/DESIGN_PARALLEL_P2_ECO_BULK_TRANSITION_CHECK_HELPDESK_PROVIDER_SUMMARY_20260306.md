# 设计文档：并行支线 P2 ECO 批量 Transition-Check + Helpdesk Provider 汇总增强

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：
  - ECO activity 批量 transition-check 预检查能力
  - Breakage cockpit/helpdesk 汇总增强（provider 与 provider_ticket_status 维度）

## 1. 目标

1. 提供 ECO 活动批量可跳转预检查，降低前端与流程编排器的串行调用成本。
2. 支持按 terminal/non-blocking 过滤候选活动，便于不同业务视图（仅关键阻塞项 / 全量项）。
3. 增强 Helpdesk 汇总可观测性，支持 provider 与 provider ticket 状态分布分析。

## 2. 方案

### 2.1 ECO 批量 transition-check

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增 `evaluate_transitions_bulk(...)`：

1. 输入：
- `eco_id`
- `to_status`（复用状态别名归一化）
- `activity_ids`（可选，若为空则取该 ECO 全量活动）
- `include_terminal`（默认 false）
- `include_non_blocking`（默认 true）
- `limit`（1..500）

2. 处理：
- 统一过滤 missing/excluded 候选。
- 对入选活动复用 `evaluate_transition(...)` 生成决策。
- 汇总 `ready/blocked/invalid/noop/missing/excluded` 计数。
- 支持 `truncated`（总量超过 limit 时只返回前 `limit` 条决策）。

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `POST /eco-activities/{eco_id}/transition-check/bulk`

错误契约：
- 业务校验失败 -> `eco_activity_transition_invalid` (400)

### 2.2 Helpdesk provider 汇总增强

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

增强 `_build_helpdesk_sync_summary(...)`：

1. 新增统计维度：
- `by_provider`
- `by_provider_ticket_status`
- `providers_total`
- `with_provider_ticket_status`

2. provider 解析优先级：
- `helpdesk_sync.provider`
- `integration.provider`
- `result.provider`
- `payload.provider`
- 默认 `stub`

3. `provider_ticket_status` 解析：
- `helpdesk_sync/result/payload` 回退链
- 仅统计非空值

## 3. 兼容性

1. 新增 ECO 接口为增量，不影响既有单条 transition-check。
2. Helpdesk 汇总字段为返回增强，兼容既有消费方。
3. 无数据库迁移。

## 4. 风险与缓解

1. 风险：批量接口返回体过大。
- 缓解：limit 上限 500 + truncated 标志。

2. 风险：activity_ids 含脏数据导致调用方难排障。
- 缓解：显式返回 `missing_activity_ids/excluded_activity_ids`。

3. 风险：provider 来源分散导致统计偏差。
- 缓解：固定字段回退链 + 默认 provider `stub`。

## 5. 验收标准

1. 批量接口可返回 ready/blocked/invalid/noop/missing/excluded 聚合计数。
2. 批量接口支持 terminal/non-blocking 过滤与 truncation。
3. cockpit helpdesk 汇总包含 provider 与 provider_ticket_status 分布。
4. service/router/e2e 受影响测试通过。
