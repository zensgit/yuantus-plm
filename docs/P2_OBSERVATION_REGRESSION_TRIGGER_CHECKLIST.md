# P2 Observation Regression Trigger Checklist

**目的**：只在真正需要时重跑 P2 observation regression，避免每次都手工判断。

---

## 1. 什么时候必须重跑

满足下面任一条，就应重跑一轮最小 P2 observation regression：

1. 改了这些运行时代码：
   - `auto-assign`
   - `escalate-overdue`
   - `dashboard summary/items/export`
   - `audit anomalies`

2. 改了这些观察工具：
   - `scripts/verify_p2_dev_observation_startup.sh`
   - `scripts/render_p2_observation_result.py`
   - `scripts/compare_p2_observation_results.py`

3. 改了这些会影响口径/权限/状态的数据面：
   - approval seed / identity seed
   - stage roles / `min_approvals` / `sla_hours`
   - auth / permission contract
   - ECO state transition wiring

4. 做了 replay / remediation，且改动触碰：
   - ECO router
   - ECO service
   - approval service
   - remote observation runbook / startup checklist 的执行语义

---

## 2. 最小重跑内容

### 2.1 采集

```bash
BASE_URL=... \
TOKEN=... \
TENANT_ID=... \
ORG_ID=... \
OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
scripts/verify_p2_dev_observation_startup.sh
```

### 2.2 渲染

```bash
python3 scripts/render_p2_observation_result.py \
  "$OUTPUT_DIR" \
  --operator "<name>" \
  --environment "<env>"
```

### 2.3 比对

```bash
python3 scripts/compare_p2_observation_results.py \
  <baseline_dir> \
  "$OUTPUT_DIR" \
  --baseline-label baseline \
  --current-label rerun
```

### 2.4 或直接单条执行

```bash
BASE_URL=... TOKEN=... [TENANT_ID=... ORG_ID=...] \
BASELINE_DIR=<baseline_dir> \
OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
scripts/run_p2_observation_regression.sh
```

---

## 3. 什么时候只做只读回归

如果改动只影响：

- 文档
- runbook
- 观察脚本
- export / render / compare 辅助工具

则通常只需要：

- baseline read path
- render
- compare

不必强制再打一发 `escalate-overdue`。

---

## 4. 什么时候要补状态迁移回归

如果改动触碰：

- escalation
- approval creation
- pending / overdue 统计
- anomaly classification

则必须补一次最小状态变化验证：

- 基线采集
- `POST /api/v1/eco/approvals/escalate-overdue`
- 再采一轮
- 用 compare 脚本输出差异

---

## 5. 什么时候要补权限三态

如果改动触碰：

- auth dependency
- permission checks
- router-level actor wiring
- service-level permission gating

则必须补：

- 未认证 `401`
- 无权限 `403`
- 有权限 `200`

重点接口：

- `POST /api/v1/eco/approvals/escalate-overdue`
- `POST /api/v1/eco/{eco_id}/auto-assign-approvers`

---

## 6. 最低通过标准

一轮 regression 至少满足：

- `summary / items / export / anomalies` 全部成功
- `OBSERVATION_RESULT.md` 生成成功
- `OBSERVATION_DIFF.md` 生成成功
- 观察面口径内部一致
- 差异能被本轮改动目标解释

---

## 7. 当前非目标

- 不把 local regression 当 shared-dev signoff
- 不因为 docs-only 变更就补一整套状态迁移实验
- 不在没有触碰权限代码时重复做全部 401/403/200 验证
