# P2 Dev Observation Startup Checklist

**Date:** 2026-04-16
**Scope:** 在开发环境中启动 `P2` 审批主链的“真实运营观察期”。

---

## 1. 目标

这份 checklist 用于把 `P2-2a / P2-2b / P2-3 / P2-3.1` 从“功能已交付”推进到“开发环境值班式观察”。

目标不是继续验证接口能不能跑通，而是验证：

- 指标是否可读
- 异常是否能定位
- 运营动作是否顺手
- 是否已经出现 `P2-4` 启动信号

配套文档：

- [P2_OPS_RUNBOOK.md](./P2_OPS_RUNBOOK.md)
- [P2_OPS_OBSERVATION_TEMPLATE.md](./P2_OPS_OBSERVATION_TEMPLATE.md)
- 执行脚本：`scripts/verify_p2_dev_observation_startup.sh`

---

## 2. 环境准备

### 2.1 固定观察环境

- 选一个固定 `dev` 环境或本地联调环境
- 保证观察期间不要频繁清库
- 明确当前使用的：
  - `base_url`
  - `tenant/org`
  - `db snapshot` 或样本数据版本

记录：

| 项 | 值 |
|---|---|
| base_url |  |
| tenant / org |  |
| 数据快照版本 |  |
| 观察周期 |  |
| 值班人 |  |

### 2.2 认证准备

至少准备两类账号：

- 普通运营/审批用户
- 有 `escalate-overdue` 权限的 admin 用户

建议先确认：

- 未认证 -> `401`
- 无权限 -> `403`
- 正常用户 / admin 用户 -> `200`

---

## 3. 端点可用性检查

启动观察前，先确认以下 6 个端点都可调用：

| 类型 | 端点 |
|---|---|
| Write | `POST /api/v1/eco/{eco_id}/auto-assign-approvers` |
| Write | `POST /api/v1/eco/approvals/escalate-overdue` |
| Read | `GET /api/v1/eco/approvals/dashboard/summary` |
| Read | `GET /api/v1/eco/approvals/dashboard/items` |
| Read | `GET /api/v1/eco/approvals/dashboard/export` |
| Read | `GET /api/v1/eco/approvals/audit/anomalies` |

最小 smoke：

```bash
TOKEN="your-jwt-token-here"
AUTH="-H 'Authorization: Bearer $TOKEN'"

curl $AUTH /api/v1/eco/approvals/dashboard/summary
curl $AUTH /api/v1/eco/approvals/audit/anomalies
```

也可以直接用执行脚本一次性收集基线证据：

```bash
BASE_URL=http://localhost:8000 \
TOKEN=your-jwt-token-here \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
scripts/verify_p2_dev_observation_startup.sh
```

---

## 4. 样本数据准备

建议最少准备 `5-10` 个 ECO，覆盖下列场景：

| 场景 | 是否覆盖 |
|---|---|
| 正常 pending |  |
| overdue |  |
| escalated |  |
| no_candidates |  |
| 不同 `eco_type` |  |
| 不同 stage 配置 |  |

建议至少包含：

- `2-3` 个不同 `eco_type`
- `2-3` 套不同 `approval_roles + min_approvals + sla_hours`

---

## 5. 基线观察

观察期开始当天先做一次基线采样：

### 5.1 Dashboard

```bash
curl $AUTH /api/v1/eco/approvals/dashboard/summary
curl $AUTH /api/v1/eco/approvals/dashboard/items
```

### 5.2 Export

```bash
curl $AUTH "/api/v1/eco/approvals/dashboard/export?fmt=csv" -o approvals_baseline.csv
```

### 5.3 Audit

```bash
curl $AUTH /api/v1/eco/approvals/audit/anomalies
```

然后把结果填进：

- [P2_OPS_OBSERVATION_TEMPLATE.md](./P2_OPS_OBSERVATION_TEMPLATE.md)

---

## 6. 运营事件演练

至少手工制造并观察这 3 类事件：

### 6.1 Overdue

- 让至少 1 个审批进入 overdue
- 确认：
  - `summary.overdue_count` 变化
  - `items` 能过滤到
  - `audit` 出现 `overdue_not_escalated`

### 6.2 No Candidates

- 制造 1 个 `approval_roles` 无活跃用户匹配的 stage
- 确认：
  - auto-assign 明确失败
  - `audit` 出现 `no_candidates`

### 6.3 Escalation

- 手工触发 1 次 `POST /api/v1/eco/approvals/escalate-overdue`
- 确认：
  - `escalated_count` 变化
  - `audit` 出现或清除对应异常
  - admin 侧 pending 可见

---

## 7. 日常节奏

### 7.1 每日晨检

- 看 `total_anomalies`
- 看 `overdue_count`
- 看 `escalated_count`
- 必要时触发一次 `escalate-overdue`
- 记录异常处理动作

### 7.2 每周复盘

- 导出一份 `dashboard export`
- 汇总：
  - `no_candidates`
  - `escalated_unresolved`
  - `overdue_not_escalated`
- 填写：
  - 配置复用观察
  - `P2-4` 启动信号周报

---

## 8. 观察重点

观察期不要只看“接口是否成功”，重点看这 4 类信号：

1. 哪些 stage 经常 overdue
2. 哪些 role 经常没人可分派
3. escalation 是否集中在某些 `eco_type`
4. 不同 `eco_type` 是否反复复用同一套审批配置

---

## 9. 退出条件

满足以下任一情况，可以结束观察期复盘：

- 已连续观察 `1-2` 周
- 已收集到足够多的异常样本
- 已经出现明确的 `P2-4` 启动信号

复盘后做三选一决策：

1. 继续观察
2. 只补轻量运营能力
3. 启动 `P2-4 Approval Template / Rule System`

---

## 10. 启动确认

| 检查项 | 状态 |
|---|---|
| 固定 dev 环境已选定 |  |
| 认证账号已准备 |  |
| 6 个端点 smoke 通过 |  |
| 样本数据已准备 |  |
| 基线观察已记录 |  |
| 3 类运营事件已演练 |  |
| 观察模板已发给值班人 |  |
| 周复盘节奏已确认 |  |
