# P2 A-lite No-Candidates Clarification

日期：2026-04-17

## 背景

`A-lite` 观察样本已经满足：

- `summary` 不再全 0
- `anomalies` 有真实记录
- `pending / overdue` 已能区分

但 `no_candidates` 未命中。

补测后确认，这不是脚本或观察流程缺陷，而是当前产品设计的直接结果。

## 设计澄清

当前实现中：

- active `superuser` 被视为所有 stage 的候选人

因此，`no_candidates` 的真实触发条件不是“调用者是非 superuser”，而是：

1. stage 需要审批
2. 没有任何 active role hit
3. **系统中不存在任何 active superuser bypass**

只要系统里仍有 active `superuser`，`no_candidates` 就可能长期保持 `0`。

## A-lite 结论

这意味着：

- `no_candidates` **不应再被当成 A-lite 启动观察期的硬门槛**
- 在有 active superuser 的运营环境里，更稳定的 RBAC 缺口信号是：
  - `auto-assign` 明确失败
  - `overdue_not_escalated`

## 文档更新

本次同步澄清到：

- `docs/P2_NO_CANDIDATES_ALITE_CHECKLIST.md`
- `docs/P2_OPS_RUNBOOK.md`
- `docs/P2_OPS_OBSERVATION_TEMPLATE.md`
- `docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md`

## 结论

- `A-lite` 观察结果可签收
- `no_candidates` 未命中不再视为 blocker
- 后续真实运营观察期继续重点看：
  - `overdue_not_escalated`
  - `escalated_unresolved`
  - `auto-assign` 失败
