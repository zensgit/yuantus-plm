# P2 Observation Regression One-Command Run

**目的**：把 `verify + render + compare` 收敛成单条命令，降低日常回归成本。

---

## 1. 什么时候用

当你已经判定“这次改动需要重跑 P2 observation regression”时，用这一条命令执行，而不是手工拼三步。

先看：

- `docs/P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST.md`

如果当前目标就是 **shared-dev 142 的 official readonly baseline**，优先先看统一 selector，而不是自己再拼 `BASELINE_DIR`：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --help
```

按目标选：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
```

如果你只是想先展开 `142` 的固定 readonly 命令，再决定是否执行：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-readonly-commands
```

如果 guard / readonly rerun 已经提示 `142` 相对 frozen baseline 漂移，但你还不准备直接 refreeze，先跑：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit
```

如果你已经确认有 drift，并且要先固定一轮 investigation evidence pack，而不是立刻 refreeze，继续用：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation
```

如果你只需要 GitHub Actions 做一轮 `current-only` probe：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-probe
```

如果你要的是 GitHub Actions 采集加 official frozen baseline readonly compare/eval：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check
```

如果这是 shared-dev 首次执行，或刚换了一组凭证，建议先跑：

```bash
scripts/precheck_p2_observation_regression.sh --env-file "$HOME/.config/yuantus/p2-observation.env"
```

---

## 2. 最小用法

### 2.1 env file 模式

```bash
ENV_FILE="$HOME/.config/yuantus/p2-observation.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL=http://<dev-host>
TOKEN=<jwt>
TENANT_ID=<tenant>
ORG_ID=<org>
ENVIRONMENT=shared-dev
ENVEOF

chmod 600 "$ENV_FILE"

OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
ARCHIVE_RESULT=1 \
BASELINE_DIR=<baseline_dir> \
scripts/run_p2_observation_regression.sh \
  --env-file "$ENV_FILE"
```

### 2.2 直接环境变量模式

```bash
BASE_URL=http://<dev-host> \
TOKEN=<jwt> \
TENANT_ID=<tenant> \
ORG_ID=<org> \
ARCHIVE_RESULT=1 \
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

如果走的是 `shared-dev 142` 的 `drift-audit` 入口，还会额外生成：

- `DRIFT_AUDIT.md`
- `drift_audit.json`

如果走的是 `shared-dev 142` 的 `drift-investigation` 入口，还会额外生成：

- `DRIFT_INVESTIGATION.md`
- `drift_investigation.json`

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

如果启用了 `ARCHIVE_RESULT=1` 或传入 `--archive`，还会有：

- `<OUTPUT_DIR>.tar.gz`

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
