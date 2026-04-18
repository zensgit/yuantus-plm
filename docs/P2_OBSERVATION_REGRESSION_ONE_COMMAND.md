# P2 Observation Regression One-Command Run

**目的**：把 `verify + render + compare` 收敛成单条命令，降低日常回归成本。

---

## 1. 什么时候用

当你已经判定“这次改动需要重跑 P2 observation regression”时，用这一条命令执行，而不是手工拼三步。

先看：

- `docs/P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST.md`

---

## 2. 最小用法

```bash
BASE_URL=http://<dev-host> \
TOKEN=<jwt> \
TENANT_ID=<tenant> \
ORG_ID=<org> \
BASELINE_DIR=<baseline_dir> \
OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
scripts/run_p2_observation_regression.sh
```

---

## 3. 它会做什么

1. 跑 `scripts/verify_p2_dev_observation_startup.sh`
2. 生成 `OBSERVATION_RESULT.md`
3. 如果提供 `BASELINE_DIR`，再生成 `OBSERVATION_DIFF.md`
4. 如果提供 `EVAL_MODE`，再生成 `OBSERVATION_EVAL.md`

---

## 4. 产物

结果目录下至少会有：

- `summary.json`
- `items.json`
- `export.json`
- `export.csv`
- `anomalies.json`
- `OBSERVATION_RESULT.md`

如果给了 `BASELINE_DIR`，还会有：

- `OBSERVATION_DIFF.md`

如果给了 `EVAL_MODE`，还会有：

- `OBSERVATION_EVAL.md`

---

## 5. 推荐参数

```bash
OPERATOR="<name>"
ENVIRONMENT="shared-dev"
BASELINE_LABEL="baseline"
CURRENT_LABEL="rerun"
```

自动判定只读回归是否通过：

```bash
EVAL_MODE="readonly"
```

自动判定状态变更回归是否命中预期：

```bash
EVAL_MODE="state-change"
EXPECT_DELTAS="overdue_count=1,escalated_count=1,items_count=1,export_json_count=1,export_csv_rows=1,escalated_unresolved=1,overdue_not_escalated=-1"
```

---

## 6. 看什么

优先只看：

- `OBSERVATION_RESULT.md`
- `OBSERVATION_DIFF.md`
- `OBSERVATION_EVAL.md`

只有在 diff 或结果异常时，再回头看原始 JSON/CSV。
