# P2 Approval Operations Runbook

**Date:** 2026-04-16
**Scope:** 审批主链运营观察指南。用于 P2-4 启动条件评估。

---

## 1. 现有能力清单

| 能力 | 端点 | 用途 |
|---|---|---|
| Auto-assign | `POST /eco/{id}/auto-assign-approvers` | 按 stage 角色自动分派 |
| Escalation | `POST /eco/approvals/escalate-overdue` | 超时升级到 admin |
| Dashboard Summary | `GET /eco/approvals/dashboard/summary` | overdue/pending/escalated 聚合 |
| Dashboard Items | `GET /eco/approvals/dashboard/items` | 带过滤的审批项列表 |
| Dashboard Export | `GET /eco/approvals/dashboard/export?fmt=csv\|json` | 导出 |
| Anomaly Audit | `GET /eco/approvals/audit/anomalies` | no_candidates / escalated_unresolved / overdue_not_escalated |

所有 dashboard 读面共享 `_base_dashboard_query`，只看 ECO 当前 stage 的 pending 审批。

> **认证前提**: 以下所有命令假设已处于认证会话中。写接口（POST）需要有效的 `Authorization: Bearer <token>` 头或等效的 session cookie。未认证调用会返回 401。
>
> **启动脚本**: 开发环境观察期启动时，可直接运行 `scripts/verify_p2_dev_observation_startup.sh` 收集 `summary/items/export/anomalies` 基线证据，并按需开启 write smoke。若环境启用了 `db-per-tenant` 或 `db-per-tenant-org`，同时传入 `TENANT_ID` / `ORG_ID`。

---

## 2. 日常运营检查

### 2.1 每日晨检

```bash
# 前提: 设置认证 token
TOKEN="your-jwt-token-here"
AUTH="-H 'Authorization: Bearer $TOKEN'"

# 1. 异常总览 — 看有没有卡住的
curl $AUTH /api/v1/eco/approvals/audit/anomalies | jq '.total_anomalies'

# 2. 超时数 — 看有没有恶化
curl $AUTH /api/v1/eco/approvals/dashboard/summary | jq '{overdue: .overdue_count, escalated: .escalated_count}'

# 3. 如果 overdue > 0 且 escalated == 0，手动触发升级（需要 eco.escalate_overdue 权限）
curl $AUTH -X POST /api/v1/eco/approvals/escalate-overdue
```

### 2.2 周报导出

```bash
# 导出本周审批项 (CSV)
curl $AUTH "/api/v1/eco/approvals/dashboard/export?fmt=csv&deadline_from=2026-04-09T00:00:00&deadline_to=2026-04-16T00:00:00" -o weekly_approvals.csv
```

### 2.3 观察结果归档

```bash
python3 scripts/render_p2_observation_result.py \
  ./tmp/p2-observation-alite/results \
  --operator "<name>" \
  --environment "shared-dev"
```

默认会在结果目录下生成 `OBSERVATION_RESULT.md`，可直接作为观察记录初稿。

### 2.4 按公司/类型切片

```bash
# 只看 ACME 公司的 BOM 类 ECO
curl $AUTH "/api/v1/eco/approvals/dashboard/summary?company_id=acme&eco_type=bom"
```

---

## 3. P2-4 启动条件（观察指标）

在日常运营中记录以下信号。当满足任一条件时，考虑启动 P2-4 (Approval Template System)：

### 信号 1: 重复配置

**观察方式**: 用 anomaly audit 的 `no_candidates` + dashboard 的 `by_stage` 交叉看

**判断标准**: 两个以上不同 ECO type（如 bom + routing）在各自的 stage 上配置了完全相同的 `approval_roles` + `min_approvals` + `sla_hours` 组合

**记录格式**:
```
日期 | ECO Type A | ECO Type B | 相同的 Stage 配置 | 备注
```

### 信号 2: 手工维护成本高

**观察方式**: 统计每周手动调 `ECOStage.approval_roles` / `min_approvals` / `sla_hours` 的次数

**判断标准**: 每周 > 3 次手动调配 → 模板化有价值

### 信号 3: 串行/并行需求

**观察方式**: 看 `by_stage` 聚合中，是否有 stage 的 pending 数量远大于 `min_approvals`

**判断标准**: 运营明确说"这个 stage 应该先 A 批再 B 批，不是同时"→ 需要串行审批

### 信号 4: Escalation 策略差异

**观察方式**: 看 `escalated_unresolved` 中，不同 eco_type 的超时行为是否应该不同

**判断标准**: 运营说"BOM ECO 超时应该找 engineering manager，routing ECO 超时应该找 ops manager"→ 需要分类 escalation policy

---

## 4. 指标口径定义

| 指标 | 定义 | 统计单位 |
|---|---|---|
| `pending_count` | ECO 在 current stage，有 pending ECOApproval，未超时 | ECOApproval 行 |
| `overdue_count` | ECO 在 current stage，有 pending ECOApproval，`approval_deadline <= now` | ECOApproval 行 |
| `escalated_count` | pending ECOApproval 且 `required_role == "admin"` | ECOApproval 行 |
| `no_candidates` | Stage 需审批且系统层面不存在任何 active role hit，且不存在 active superuser bypass | ECO × Stage 对 |
| `escalated_unresolved` | Admin ECOApproval pending on current stage | ECOApproval 行 |
| `overdue_not_escalated` | 超时但无 admin ECOApproval 存在 | ECO × Stage 对 |

**所有指标只看 ECO 当前 stage**。历史 stage 的 pending 不计入。

**`by_role` 按 stage 配置的 `approval_roles` 聚合**，不是按 assignee 实际持有的 RBAC 角色。

**`no_candidates` 在存在 active superuser 的环境里可能长期为 0**。这是当前产品设计的一部分，不应单独被当成观察失败；此时可结合：

- `overdue_not_escalated`
- `auto-assign` 明确失败

一起判断 RBAC 配置缺口。

---

## 5. 告警建议

| 条件 | 动作 |
|---|---|
| `total_anomalies > 0` | 晨检时人工确认 |
| `no_candidates` 连续出现同一 stage | 补 RBAC 角色或调整 stage 配置 |
| `overdue_not_escalated > 0` | 触发 `POST /escalate-overdue` |
| `escalated_unresolved` 超过 24h | 人工联系 admin |

补充：

- 如果环境存在 active superuser，`no_candidates = 0` 不代表没有 RBAC 缺口
- 这时优先看 `auto-assign` 失败与 `overdue_not_escalated`

---

## 6. 已签收交付清单

| Delivery | Doc | Tests |
|---|---|---|
| P2-2a Auto-assign R5 | `DEV_AND_VERIFICATION_P2_2a_APPROVAL_AUTO_ASSIGN.md` | 26 |
| P2-2b Escalation R2 | `DEV_AND_VERIFICATION_P2_2b_OVERDUE_ESCALATION.md` | 12 |
| P2-2 Unified | `DEV_AND_VERIFICATION_P2_2_APPROVAL_CHAIN_DELIVERY.md` | — |
| P2-3 Dashboard R2 | `DEV_AND_VERIFICATION_P2_3_SLA_DASHBOARD.md` | 17→28 |
| P2-3.1 PR-1 Filters | `DEV_AND_VERIFICATION_P2_3_1_PR1_DASHBOARD_FILTERS.md` | 28 |
| P2-3.1 PR-2 Export | `DEV_AND_VERIFICATION_P2_3_1_PR2_DASHBOARD_EXPORT.md` | 11 |
| P2-3.1 PR-3 Audit R2 | `DEV_AND_VERIFICATION_P2_3_1_PR3_APPROVAL_OPS_AUDIT.md` | 9 |
| **Full regression** | | **241 passed** |
