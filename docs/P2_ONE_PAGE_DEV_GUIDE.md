# P2 One-Page Dev Guide

**适用范围**：开发阶段 / shared dev 观察前后  
**目标**：不要翻整套文档，只用这一页完成执行与判断

---

## 1. 你平时只需要看什么

日常只看这 3 个文件：

- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md`
- `docs/P2_OPS_RUNBOOK.md`

如果要判断“这次改动是否必须重跑回归”，再加看：

- `docs/P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST.md`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/P2_OBSERVATION_REGRESSION_EVALUATION.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`

其余 `DEV_AND_VERIFICATION_*` 文档默认都当归档，不需要日常阅读。

---

## 2. 你真正要跑的命令

### 2.0 先判定你走哪条 shared-dev 路径

如果你不确定当前 shared-dev 能不能重置，不要先碰 bootstrap，默认按 **existing shared-dev rerun** 处理。

直接看：

- `bash scripts/print_p2_shared_dev_mode_selection.sh`

结论只有两条：

- **不确定能否重置 / 环境可能已在用**：
  - `bash scripts/print_p2_shared_dev_observation_commands.sh`
- **明确可以重置 / fresh shared-dev**：
  - `bash scripts/print_p2_shared_dev_first_run_commands.sh`

如果当前环境就是 **shared-dev 142 的 official readonly baseline**，不要手工再找 `BASELINE_DIR`，直接用：

- `bash scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`

### 2.1 首选：env file + 本地 precheck

如果不想每次重新 `export` shared-dev 凭证，先在本地准备一个不入库的 env 文件：

```bash
ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL=http://<dev-host>
TOKEN=<jwt>
TENANT_ID=<tenant>
ORG_ID=<org>
ENVIRONMENT=shared-dev
ENVEOF

chmod 600 "$ENV_FILE"
```

先跑本地 precheck：

```bash
scripts/precheck_p2_observation_regression.sh \
  --env-file "$ENV_FILE"
```

这一步只验证：

- 认证是否可用
- `summary` 读接口是否可达
- 产物是否能落地：
  - `OBSERVATION_PRECHECK.md`
  - `observation_precheck.json`

### 2.2 env file + 单条 shell wrapper

确认 precheck 绿后，再跑：

```bash
OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
ARCHIVE_RESULT=1 \
scripts/run_p2_observation_regression.sh \
  --env-file "$ENV_FILE"
```

这会额外生成同级归档：

```text
<OUTPUT_DIR>.tar.gz
```

### 2.3 直接环境变量：单条 shell wrapper

```bash
BASE_URL=http://<dev-host> TOKEN=<jwt> [TENANT_ID=... ORG_ID=...] \
ARCHIVE_RESULT=1 \
OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
scripts/run_p2_observation_regression.sh
```

如果没有现成 `JWT`，可直接让 wrapper 登录：

```bash
BASE_URL=http://<dev-host> USERNAME=<user> PASSWORD=<password> [TENANT_ID=... ORG_ID=...] \
ARCHIVE_RESULT=1 \
OUTPUT_DIR=./tmp/p2-observation-rerun-$(date +%Y%m%d-%H%M%S) \
scripts/run_p2_observation_regression.sh
```

### 2.4 GitHub workflow 入口

如果你不想在本地 shell 里手工拼 `gh workflow run/list/watch/download`，直接用：

```bash
scripts/run_p2_observation_regression_workflow.sh \
  --base-url http://<dev-host> \
  --tenant-id <tenant> \
  --org-id <org> \
  --environment shared-dev \
  --out-dir ./tmp/p2-observation-workflow-$(date +%Y%m%d-%H%M%S)
```

这条命令会：

1. 触发 `p2-observation-regression`
2. 等待 workflow 完成
3. 下载 `p2-observation-regression` artifact
4. 生成 `WORKFLOW_DISPATCH_RESULT.md`

### 2.5 原始 verify/render 命令

只有在你需要调试最底层采集脚本时，才回到这组命令：

```bash
BASE_URL=http://<dev-host> \
TOKEN=<jwt> \
TENANT_ID=<tenant> \
ORG_ID=<org> \
OUTPUT_DIR=./tmp/p2-observation-shared-dev-$(date +%Y%m%d-%H%M%S) \
scripts/verify_p2_dev_observation_startup.sh
```

```bash
python3 scripts/render_p2_observation_result.py \
  "$OUTPUT_DIR" \
  --operator "<name>" \
  --environment "shared-dev"
```

### 2.6 可选：和基线做差异对比

```bash
python3 scripts/compare_p2_observation_results.py \
  <baseline_dir> \
  "$OUTPUT_DIR" \
  --baseline-label baseline \
  --current-label current
```

### 2.7 自动判定是否通过

```bash
python3 scripts/evaluate_p2_observation_results.py \
  "$OUTPUT_DIR" \
  --mode readonly \
  --baseline-dir <baseline_dir>
```

如果这轮本来就预期会发生状态迁移，则改用：

```bash
python3 scripts/evaluate_p2_observation_results.py \
  "$OUTPUT_DIR" \
  --mode state-change \
  --baseline-dir <baseline_dir> \
  --expect-delta overdue_count=1 \
  --expect-delta escalated_count=1
```

### 2.8 只在需要时直接用原始 gh 命令

如果你只是想最小化触发，不需要本地等待和下载，也可以直接用：

```bash
gh workflow run p2-observation-regression \
  --field base_url=http://<dev-host> \
  --field tenant_id=<tenant> \
  --field org_id=<org> \
  --field environment=shared-dev
```

---

## 3. 你只需要看什么结果

优先只看：

- `$OUTPUT_DIR/OBSERVATION_RESULT.md`
- `$OUTPUT_DIR/OBSERVATION_EVAL.md`

不要先钻：

- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`

只有在 `OBSERVATION_RESULT.md` 显示异常时，再回头看原始产物。
如果 `OBSERVATION_EVAL.md` 已失败，先修口径或期望，再做业务判断。

---

## 4. 你只需要做什么判断

当前阶段**不是**决定 `P2-4`，只做这 3 个判断：

1. 这轮 shared dev 观察是否正常跑通
2. 有没有明显异常
3. 是否需要继续观察或人工介入

---

## 5. 什么叫“正常”

至少满足：

- `summary/items/export/anomalies` 都返回成功
- 生成了 `OBSERVATION_RESULT.md`
- `OBSERVATION_RESULT.md` 里能看懂：
  - `pending`
  - `overdue`
  - `anomalies`

---

## 6. 什么异常最值得看

优先只看这 3 类：

- `overdue_not_escalated`
- `escalated_unresolved`
- `auto-assign` 明确失败

补充：

- `no_candidates` 在有 active `superuser` 的环境里可能长期为 `0`
- 这不一定是 bug，也不单独算观察失败

---

## 7. 什么时候再找 Codex

出现下面任一情况再回传结果：

- `OBSERVATION_RESULT.md` 显示异常数明显增加
- `overdue` 和 `escalated` 的变化对不上
- `auto-assign` 返回值和 audit/dashboards 对不上
- 你不确定这轮结果该归因于数据、权限还是代码

回传时最少给：

- `OBSERVATION_RESULT.md`
- `summary.json`
- `anomalies.json`
- `README.txt`

---

## 8. 当前不做什么

- 不再补本地轮次
- 不再造 local seed 样本
- 不启动 `P2-4`
- 不做 `BOM Diff / CAD Viewer / ECM sunset`

开发阶段现在的目标只有一个：  
**把 shared dev 观察跑通并留痕。**
