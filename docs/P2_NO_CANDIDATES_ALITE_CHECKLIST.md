# P2 No-Candidates A-lite Checklist

日期：2026-04-17

## 目标

在不改产品代码的前提下，补一条最小 `no_candidates` 观察样本。

本清单专门用于覆盖当前 `A-lite` 结果中还未真实命中的异常类型：

- `no_candidates`

## 设计前提

当前系统设计里：

- `superuser` 被视为所有 stage 的候选人

所以如果当前环境里存在任一 active `superuser/admin`，即使 stage 的 `approval_roles` 无人匹配，也**不会**触发 `no_candidates`。

要命中 `no_candidates`，必须满足：

1. stage 需要审批
2. stage 的 `approval_roles` 没有任何 active user 匹配
3. 系统里不存在任何 active `superuser` 作为候选 bypass

## 最小执行步骤

### 1. 准备非 superuser 用户

准备一名普通用户，例如：

- `username`: `ops-viewer`
- 非 superuser
- 只给基础登录能力，不给 stage 对应角色

### 2. 准备一个需要审批的 stage

要求：

- `approval_type != none`
- `approval_roles` 指向一个当前没有 active user 命中的角色

例如：

- stage 需要 `quality-manager`
- 当前没有任何 active `quality-manager`

### 3. 用非 superuser 跑 auto-assign

目标是命中：

- `POST /api/v1/eco/{eco_id}/auto-assign-approvers`

预期：

- 明确失败
- 错误语义指向 “no active users with matching active roles”

### 4. 看 anomaly audit

执行：

```bash
curl $AUTH /api/v1/eco/approvals/audit/anomalies
```

预期：

- 只有在**系统层面无 active superuser** 时，`no_candidates` 才可能出现

## 最小验收

| 目标 | 预期 |
|---|---|
| auto-assign 不应静默成功 | 返回明确失败 |
| audit 应记录异常 | 仅在无 active superuser 环境下期待 `no_candidates >= 1` |
| 不依赖修改运行时代码 | 是 |

## 建议回收的证据

- `auto-assign` 的 HTTP 响应
- `anomalies.json`
- 相关 ECO / stage 标识
- 执行时使用的用户说明（确认其非 superuser）

## 结论填写

| 项 | 结果 |
|---|---|
| 是否命中 `no_candidates` |  |
| 是否确认当前环境仍有 active superuser bypass |  |
| 是否可并入观察模板 |  |
