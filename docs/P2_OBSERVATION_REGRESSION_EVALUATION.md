# P2 Observation Regression Evaluation

**目的**：把 `OBSERVATION_RESULT.md / OBSERVATION_DIFF.md` 之后的“是否通过”判断收成可执行规则。

---

## 1. 什么时候用

在你已经拿到一轮 observation artifacts 后，用这个脚本做最后一步：

- `current-only`: 只验证单个结果目录内部口径是否自洽
- `readonly`: 验证这轮只读回归是否和基线稳定一致
- `state-change`: 验证这轮状态迁移是否满足显式预期 delta

---

## 2. 最小用法

### 2.1 current-only

```bash
python3 scripts/evaluate_p2_observation_results.py \
  <current_dir> \
  --mode current-only
```

### 2.2 readonly

```bash
python3 scripts/evaluate_p2_observation_results.py \
  <current_dir> \
  --mode readonly \
  --baseline-dir <baseline_dir>
```

### 2.3 state-change

```bash
python3 scripts/evaluate_p2_observation_results.py \
  <current_dir> \
  --mode state-change \
  --baseline-dir <baseline_dir> \
  --expect-delta overdue_count=1 \
  --expect-delta escalated_count=1 \
  --expect-delta items_count=1 \
  --expect-delta export_json_count=1 \
  --expect-delta export_csv_rows=1 \
  --expect-delta escalated_unresolved=1 \
  --expect-delta overdue_not_escalated=-1
```

---

## 3. 它会检查什么

所有模式都会检查：

- `items.json / export.json / export.csv` 行数一致
- `summary.pending_count / overdue_count / escalated_count` 与 `items.json` 推导一致
- `anomalies.total_anomalies` 与各 anomaly bucket 数量一致

`readonly` 额外检查：

- 核心 metric 相对基线保持不变

`state-change` 额外检查：

- 你显式声明的 delta 是否逐条命中

---

## 4. 产物

默认会生成：

- `<current_dir>/OBSERVATION_EVAL.md`

脚本返回码：

- `0`: 全部检查通过
- `1`: 至少一条检查失败

---

## 5. 推荐搭配

推荐顺序：

1. `scripts/verify_p2_dev_observation_startup.sh`
2. `scripts/render_p2_observation_result.py`
3. `scripts/compare_p2_observation_results.py`
4. `scripts/evaluate_p2_observation_results.py`

或者直接用：

```bash
EVAL_MODE=readonly \
BASE_URL=... TOKEN=... BASELINE_DIR=... \
scripts/run_p2_observation_regression.sh
```

---

## 6. 边界

- 这个脚本只验证“口径是否一致”和“显式期望是否命中”
- 它不会替你决定业务上“这个状态变化是否合理”
- `state-change` 模式下，不要省略 `--expect-delta`，否则就会退化成模糊检查
