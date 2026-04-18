# P2 Observation Regression Audit

日期：2026-04-18
仓库基线：`fef079c`
观察环境：`local-dev-env`（本机 `sqlite + uvicorn`，非 shared dev）
Base URL：`http://127.0.0.1:7910`
Tenant / org：`tenant-1 / org-1`

## 目标

在 `main` 已完成前序 replay / script remediation 后，按最小回归协议确认 P2 审批观察面没有失真，重点只看 4 类：

- 读面一致性：`summary / items / export / anomalies`
- 状态迁移：`escalate-overdue`
- 权限语义：`401 / 403 / 200`
- 工具链可用性：`verify_p2_dev_observation_startup.sh` 与 `render_p2_observation_result.py`

## 执行流程

### 1. 启动固定本地观察环境

使用当前仓库内的 `local-dev-env` 种子环境：

- `admin / admin`：superuser
- `ops-viewer / ops123`：非 superuser
- 本轮种子覆盖：
  - `eco-pending`
  - `eco-overdue-admin`
  - `eco-overdue-opsview`
  - `eco-specialist`

### 2. 基线采集

执行：

```bash
BASE_URL=http://127.0.0.1:7910 TOKEN=$ADMIN_TOKEN \
TENANT_ID=tenant-1 ORG_ID=org-1 \
OUTPUT_DIR=tmp/p2-observation-regression-20260418/baseline \
bash scripts/verify_p2_dev_observation_startup.sh

python3 scripts/render_p2_observation_result.py \
  tmp/p2-observation-regression-20260418/baseline \
  --operator chouhua --environment local-dev-env-baseline
```

### 3. 最小状态变化验证

先验证权限门，再用 `admin` 执行一次真实状态迁移：

```bash
POST /api/v1/eco/approvals/escalate-overdue
```

随后再次执行 `verify` 与 `render`：

```bash
BASE_URL=http://127.0.0.1:7910 TOKEN=$ADMIN_TOKEN \
TENANT_ID=tenant-1 ORG_ID=org-1 \
OUTPUT_DIR=tmp/p2-observation-regression-20260418/after-escalate \
bash scripts/verify_p2_dev_observation_startup.sh

python3 scripts/render_p2_observation_result.py \
  tmp/p2-observation-regression-20260418/after-escalate \
  --operator chouhua --environment local-dev-env-after-escalate
```

### 4. 权限三态验证

验证两条写接口：

- `POST /api/v1/eco/approvals/escalate-overdue`
- `POST /api/v1/eco/{eco-specialist}/auto-assign-approvers`

分别观察：

- 未认证：`401`
- `ops-viewer`：`403`
- `admin`：`200`

## 结果 A - 读面一致性

### 基线

| 观察面 | 结果 |
|---|---|
| `summary` | `pending_count=1`, `overdue_count=2`, `escalated_count=0` |
| `items` | `3` 条 |
| `export.json` | `3` 条 |
| `export.csv` | `3` 条数据行 |
| `anomalies` | `total_anomalies=2`, `no_candidates=0`, `escalated_unresolved=0`, `overdue_not_escalated=2` |

### escalation 后

| 观察面 | 结果 |
|---|---|
| `summary` | `pending_count=1`, `overdue_count=3`, `escalated_count=1` |
| `items` | `4` 条 |
| `export.json` | `4` 条 |
| `export.csv` | `4` 条数据行 |
| `anomalies` | `total_anomalies=2`, `no_candidates=0`, `escalated_unresolved=1`, `overdue_not_escalated=1` |

结论：

- 基线与迁移后都满足：`items == export.json == export.csv`
- 基线与迁移后都满足：`summary.pending_count + summary.overdue_count == items`
- `anomalies.total_anomalies` 与异常子类总数一致
- 本轮没有发现 `summary / items / export / anomalies` 互相对不上的失真

## 结果 B - 最小状态变化验证

`admin` 执行：

```bash
POST /api/v1/eco/approvals/escalate-overdue
```

返回：

```json
{"escalated":1,"items":[{"eco_id":"ba36f241-d285-4165-83f8-7694079fc750","stage_id":"8c72a244-49bc-47d9-b912-6d6f98dd3327","hours_overdue":3.011281177222222,"escalated":[{"escalated_to_user_id":1,"escalated_to_username":"admin","approval_id":"2d23c4d3-1ae1-4ddf-9af4-af3204b36a1d"}]}]}
```

关键变化如下：

| 指标 | 基线 | migration 后 | 结论 |
|---|---:|---:|---|
| `items_count` | `3` | `4` | 新增 1 条 escalated approval |
| `pending_count` | `1` | `1` | 未过期 pending 不变 |
| `overdue_count` | `2` | `3` | 新增的 escalated approval 也已处于 overdue |
| `escalated_count` | `0` | `1` | 命中预期 |
| `overdue_not_escalated` | `2` | `1` | 命中预期 |
| `escalated_unresolved` | `0` | `1` | 命中预期 |

解释：

- 本轮被提升的是 `eco-overdue-opsview`
- `eco-overdue-admin` 仍保留在 `overdue_not_escalated`
- 因为新建的 escalated approval 继承了当前超期事实，所以 `overdue_count` 从 `2 -> 3`，这与当前实现一致，不是失真

## 结果 C - 权限语义

### `escalate-overdue`

| 调用方 | HTTP | 结果 |
|---|---:|---|
| 未认证 | `401` | `{\"detail\":\"Unauthorized\"}` |
| `ops-viewer` | `403` | `{\"detail\":\"Forbidden: insufficient ECO permission\"}` |
| `admin` | `200` | `escalated=1` |

### `auto-assign-approvers`

| 调用方 | HTTP | 结果 |
|---|---:|---|
| 未认证 | `401` | `{\"detail\":\"Unauthorized\"}` |
| `ops-viewer` | `403` | `{\"detail\":\"Forbidden: insufficient ECO permission\"}` |
| `admin` | `200` | 成功为 `eco-specialist` 分派 approver |

结论：

- 未认证 / 无权限 / 有权限 三态语义没有漂
- 本轮重点观察的两条写接口都符合 `401 / 403 / 200` 预期

## 结果 D - 工具链

本轮两次完整跑通：

- `scripts/verify_p2_dev_observation_startup.sh`
- `scripts/render_p2_observation_result.py`

产物目录：

- `tmp/p2-observation-regression-20260418/baseline`
- `tmp/p2-observation-regression-20260418/after-escalate`
- `tmp/p2-observation-regression-20260418/notes/summary_report.json`

对应结果文件：

- `tmp/p2-observation-regression-20260418/baseline/OBSERVATION_RESULT.md`
- `tmp/p2-observation-regression-20260418/after-escalate/OBSERVATION_RESULT.md`

结论：

- 观察脚本链没有断
- 当前 `main` 可以稳定支持后续同类 regression re-run

## 最终结论

- 本轮没有发现 P2 审批观察面失真
- 读面一致性、状态迁移、权限语义、工具链可用性均符合预期
- 因此本轮不做新的 service/router remediation，只固化本次 regression audit
- 后续每次回归仍建议只盯这 4 类：`summary/items/export/anomalies`、`escalate-overdue`、`401/403/200`、`verify/render` 工具链
