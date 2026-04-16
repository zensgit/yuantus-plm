# P2 Approval Operations Observation Template

**Date:** 2026-04-16
**Scope:** `P2-2a / P2-2b / P2-3 / P2-3.1` 已签收后的真实运营观察记录模板。

---

## 1. 使用说明

- 本模板配合 [P2_OPS_RUNBOOK.md](./P2_OPS_RUNBOOK.md) 使用。
- 建议频率：
  - `每日`: 填写晨检记录和异常明细
  - `每周`: 汇总配置复用观察和 `P2-4` 启动信号
- 所有指标口径以 runbook 第 4 节为准，不另起一套定义。

---

## 2. 每日晨检记录

| 日期 | total_anomalies | overdue_count | escalated_count | 是否手动触发 escalation | 导出文件 | 值班人 | 备注 |
|---|---:|---:|---:|---|---|---|---|
| 2026-04-16 | 0 | 0 | 0 | 否 | `weekly_approvals_20260416.csv` |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

建议晨检时至少执行：

```bash
curl $AUTH /api/v1/eco/approvals/audit/anomalies
curl $AUTH /api/v1/eco/approvals/dashboard/summary
```

---

## 3. 异常明细记录

| 日期 | anomaly_type | eco_id | stage_id | company_id | eco_type | 当前处理人 | 处理动作 | 状态 | 关闭时间 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-04-16 | `no_candidates` |  |  |  |  |  | 补 RBAC 角色 | open |  |  |
|  | `escalated_unresolved` |  |  |  |  |  | 联系 admin |  |  |  |
|  | `overdue_not_escalated` |  |  |  |  |  | 手动触发 escalation |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |

说明：
- `no_candidates`: stage 需要审批，但没有 active users with matching active roles
- `escalated_unresolved`: 已升级到 admin，但仍 pending
- `overdue_not_escalated`: 已超时，但尚未升级

---

## 4. 配置复用观察

| 日期 | company_id | eco_type | stage_name | approval_roles | min_approvals | sla_hours | 是否与其他类型重复 | 重复对象 | 证据 | 备注 |
|---|---|---|---|---|---:|---:|---|---|---|---|
| 2026-04-16 |  | `bom` |  | `engineering, qa` | 1 | 24 | 否 |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |

用于判断：
- 是否已经出现重复审批配置
- 是否值得把手工 stage 配置抽象为模板

---

## 5. P2-4 启动信号周报

| 周期 | 重复配置信号 | 串行/并行诉求 | escalation 分类差异 | 每周手工维护次数 | 是否建议启动 P2-4 | 负责人 | 下次复盘时间 | 备注 |
|---|---|---|---|---:|---|---|---|---|
| 2026-W16 | 否 | 否 | 否 | 0 | 否 |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |

建议判断标准：
- `重复配置信号`: 两个以上不同 `eco_type` 复用同一套 `approval_roles + min_approvals + sla_hours`
- `串行/并行诉求`: 运营明确提出顺序审批需求
- `escalation 分类差异`: 不同 `eco_type` 需要不同升级目标
- `每周手工维护次数`: 对 `approval_roles / min_approvals / sla_hours` 的人工调整次数

---

## 6. 周复盘摘要

```text
本周时间范围:
值班/复盘人:

1. 晨检总体情况:
- total_anomalies 峰值:
- overdue_count 峰值:
- escalated_count 峰值:

2. 主要异常:
- no_candidates:
- escalated_unresolved:
- overdue_not_escalated:

3. 配置复用观察:
- 是否存在重复 stage 配置:
- 是否需要分类 escalation:
- 是否出现串行/并行审批诉求:

4. 建议:
- 是否继续观察:
- 是否需要补 RBAC / stage 配置:
- 是否满足 P2-4 启动条件:
```

---

## 7. 附：建议保留的证据

- `dashboard summary` 的 JSON 截图或导出
- `dashboard export` 的 CSV
- `audit anomalies` 的原始输出
- 当周手工触发 escalation 的命令记录
- 运营备注或工单链接
