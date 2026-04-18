# P2 Local A-lite Observation — Three-Round Closure

**Date:** 2026-04-17
**Environment:** `local-a-lite` (single-node local dev, not shared dev)
**Operator:** Claude (local dev smoke)
**Main baseline:** `7f02ff6` (after #228 merge)

---

## 1. 性质声明

| 项 | 值 |
|---|---|
| 环境类型 | **local-a-lite**（本地单机 + sqlite） |
| 用户数据 | 3-5 条手工 seed 的 ECO |
| 时间尺度 | < 1 小时 |
| 目的 | **验证观察工具链与异常/状态语义是否闭环** |
| **不等同于** | shared dev 真实观察期 |

本文档是工具链自证记录。真实运营观察必须在 shared dev 环境跑，数据来自真实业务流，时间跨度至少 1-2 周。不要把本文档的数字和 shared dev 基线混用。

---

## 2. Round 1: Baseline

**目标:** `summary/items/anomalies/export` 全部成功 + `OBSERVATION_RESULT.md` 生成

| 指标 | 值 |
|---|---|
| `pending_count` | 2 |
| `overdue_count` | 1 |
| `escalated_count` | 0 |
| `overdue_not_escalated` | 1 |

**验收:** ✅ 5 端点全部 200；渲染器产出 `OBSERVATION_RESULT.md`

**证据:** `tmp/p2-observation-alite/round1-baseline/`

---

## 3. Round 2: Overdue / Escalation

**目标:** 状态变化能被观察面捕获

**步骤:**
1. 造一条新 overdue ECO（`ECO-overdue-round2`，assignee=`ops-viewer`，deadline -3h）以便 escalation 能生效
2. Pre-escalation 快照
3. `POST /eco/approvals/escalate-overdue`
4. Post-escalation 快照

| 指标 | Before | After | Δ |
|---|---|---|---|
| `pending_count` | 2 | 2 | 0 |
| `overdue_count` | 2 | 3 | +1（新 admin ECOApproval 也计入） |
| `escalated_count` | 0 | 1 | **+1** |
| `overdue_not_escalated` | 2 | 1 | **-1** |
| `escalated_unresolved` | 0 | 1 | **+1** |

**Escalate response:**
```json
{"escalated": 1, "items": [{"eco_id": "b578e586...", "hours_overdue": 3.0,
  "escalated": [{"escalated_to_user_id": 1, "escalated_to_username": "admin"}]}]}
```

**验收:** ✅ 观察面精确捕获 `overdue_not_escalated → escalated_unresolved` 的状态迁移

**证据:** `tmp/p2-observation-alite/round2a-before-escalate/`, `round2-escalate-response.json`, `round2b-after-escalate/`

---

## 4. Round 3: RBAC / Assignment

**目标:** auto-assign 语义明确（成功 / 失败 / superuser bypass）

| 场景 | Actor | Stage | HTTP | Response |
|---|---|---|---|---|
| A. 成功 | admin (superuser) | Review | 200 | `assigned=[admin]` |
| B. 权限拒绝 | ops-viewer (non-superuser) | SpecialistReview | **403** | `"Forbidden: insufficient ECO permission"` |
| C. Superuser bypass | admin (superuser) | SpecialistReview(specialist role，无 non-superuser 匹配) | 200 | `assigned=[admin]`（admin 以 superuser 身份兜底） |

**验收:**
- A: ✅ auto-assign 非静默成功，返回具体 `assigned[]` + `approval_request_ids`
- B: ✅ 失败返回 403 + 明确 detail
- C: ✅ superuser bypass 行为被观察面记录；解释了 `no_candidates` 在带 active superuser 环境中永为 0

**证据:** `tmp/p2-observation-alite/round3-rbac/{a_admin_success,b_ops_forbidden,c_admin_on_specialist}.json`

---

## 5. 退出标准对账

| 标准 | 结果 |
|---|---|
| 1 次非空 baseline | ✅ Round 1 |
| 1 次异常命中 | ✅ overdue_not_escalated=1→2 |
| 1 次状态变化被 dashboard/audit 正确反映 | ✅ Round 2 pre/post escalation 5 指标全部正确变化 |
| 1 次 assignment/RBAC 语义验证 | ✅ Round 3 三场景 |
| 至少 2-3 份 `OBSERVATION_RESULT.md` | ✅ 3 份已生成 |

---

## 6. 关键发现（移交 shared dev 时需注意）

1. **Escalation idempotent guard**
   - 若 overdue ECO 的现有 pending ECOApproval 已属 admin，`escalate-overdue` 跳过（escalated=0）
   - 要触发升级需要一条 "overdue + 非-admin 为唯一 pending" 的 ECO

2. **`no_candidates` 永不命中带 active superuser 的环境**
   - `_resolve_candidate_users` 对每个 stage 都把 active superusers 视为候选人
   - 这是设计（运营 bypass），不是 bug
   - RBAC 缺口应结合 `overdue_not_escalated` + auto-assign 403 信号判断

3. **auto-assign 权限门真实有效**
   - 路由层 `get_current_user_id`（401）+ service 层 `_check_user_eco_permission`（403）双层
   - non-superuser 无 `eco.auto_assign` permission → 403

4. **状态转换可对账**
   - `overdue_not_escalated` 和 `escalated_unresolved` 是互补集合
   - Escalation 执行后，一条 ECO 从前者迁移到后者

---

## 7. 阶段性结论

> **P2 开发阶段观察闭环已完成；下一阶段是 shared dev 真实观察，不再继续本地扩样本。**

- ✅ 工具链自证：采集（`verify_p2_dev_observation_startup.sh`）+ 渲染（`render_p2_observation_result.py`）闭环
- ✅ 异常/状态语义自证：`overdue_not_escalated`、`escalated_unresolved`、auto-assign 403 均可观察
- ⏸️ 暂停开发侧本地观察补样本
- ⏳ 等 shared dev 环境可用后，使用相同工具跑真实 baseline

---

## 8. 本地环境局限（不扩展）

- 数据量：3-5 条手工 seed ECO，不代表真实运营
- `superuser bypass` 在本环境掩盖了部分 RBAC 分支
- 时间尺度 < 1 小时，不覆盖 1-2 周真实观察窗
- 仅 sqlite，未验证 Postgres 行为差异

**这些局限是故意保留的。要补全，必须是 shared dev，不是堆本地轮次。**

---

## 9. 产出目录（归档位置）

```
tmp/p2-observation-alite/
├── round1-baseline/
│   ├── summary.json items.json export.{csv,json} anomalies.json README.txt
│   └── OBSERVATION_RESULT.md
├── round2a-before-escalate/
├── round2b-after-escalate/
│   └── OBSERVATION_RESULT.md
├── round2-escalate-response.json
├── round3-rbac/
│   ├── a_admin_success.json b_ops_forbidden.json c_admin_on_specialist.json
│   └── OBSERVATION_RESULT.md
└── ROUNDS_SUMMARY_20260417.md
```
