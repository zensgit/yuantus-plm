# DEV / Verification - Shared-dev 142 Readonly Refreeze

日期：2026-04-19
仓库基线：`5565c95`（`fix(deploy): pin shared-dev first-run to base compose (#264)`）

## 背景

`142` 上的 shared-dev 已在同日完成 first-run、一次 `escalate-overdue`，以及额外的权限三态写接口验证。

本轮目标不是重新做 fresh bootstrap，而是回答两个问题：

1. 最新 `origin/main` 下，`precheck + observation regression` 工具链是否仍能跑通
2. 当前远端观察面是否还能作为稳定 readonly baseline

## 目标环境

- remote host:
  - `142.171.239.56`
- operator repo:
  - `/tmp/yuantus-shared-dev-rerun-20260419`
- observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`

## 执行过程

### 1. 在最新主线 clean worktree 上重跑

为避免污染操作者当前未提交工作树，本轮在 clean worktree 上执行：

```bash
git worktree add /tmp/yuantus-shared-dev-rerun-20260419 origin/main
```

该 worktree 对应的最新主线 commit 为：

- `5565c95`

### 2. 先跑 precheck

执行：

```bash
OUTPUT_DIR="/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-observation-precheck-20260419-rerun" \
ENVIRONMENT="shared-dev-142-readonly-precheck" \
bash scripts/precheck_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

结果：

- `SUMMARY_HTTP_STATUS=200`

说明：

- 最新主线下，本地 wrapper 到真实 shared-dev 的认证与 summary probe 仍然是通的

### 3. 第一次 readonly rerun

最初将 `2026-04-19` 的 `after-escalate` 结果当作 frozen baseline：

- baseline:
  - `/Users/chouhua/Downloads/Github/Yuantus/tmp/p2-shared-dev-observation-20260419-174003-after-escalate`

执行：

```bash
OUTPUT_DIR="/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly" \
BASELINE_DIR="/Users/chouhua/Downloads/Github/Yuantus/tmp/p2-shared-dev-observation-20260419-174003-after-escalate" \
BASELINE_LABEL="20260419-after-escalate" \
CURRENT_LABEL="20260419-rerun" \
EVAL_MODE="readonly" \
ENVIRONMENT="shared-dev-142-readonly" \
ARCHIVE_RESULT=1 \
bash scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

这一步 `verify + render` 跑通，但 `OBSERVATION_EVAL.md` 返回 `FAIL`。

失败点只集中在：

- `pending_count`: `1 -> 2`
- `items_count`: `4 -> 5`
- `export_json_count`: `4 -> 5`
- `export_csv_rows`: `4 -> 5`

其余关键指标保持稳定：

- `overdue_count = 3`
- `escalated_count = 1`
- `total_anomalies = 2`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`

### 4. 失败归因

逐项比对 `items.json` 后，确认当前环境只比旧 baseline 多出 1 条 approval：

- `stage_name = SpecialistReview`
- `assignee_username = admin`
- `is_overdue = false`
- `is_escalated = false`

这与当日 first-run 记录完全一致：

- `admin -> auto-assign-approvers` 是在 `after-escalate` 状态采集之后补打，用于补齐权限三态
- 因此它不会出现在旧的 `after-escalate` diff/eval 基线里
- 但它会真实改变远端环境，导致后续 readonly rerun 比旧基线多出 1 条 pending item

结论：

- 这不是新的 service/router regression
- 这是 baseline 失效，而不是观察面失真

### 5. 重新冻结 readonly baseline

为验证当前远端环境是否稳定，再次把“第一次 readonly rerun 的当前结果”当作新 baseline，立即复跑一次：

```bash
OUTPUT_DIR="/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly-freeze" \
BASELINE_DIR="/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly" \
BASELINE_LABEL="20260419-rerun-1" \
CURRENT_LABEL="20260419-rerun-2" \
EVAL_MODE="readonly" \
ENVIRONMENT="shared-dev-142-readonly-freeze" \
ARCHIVE_RESULT=1 \
bash scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

结果：

- `OBSERVATION_EVAL.md`: `PASS`
- `20/20 passed`

## 当前冻结基线

重新冻结后的 readonly baseline 为：

- `pending_count=2`
- `overdue_count=3`
- `escalated_count=1`
- `items_count=5`
- `export_json_count=5`
- `export_csv_rows=5`
- `total_anomalies=2`
- `no_candidates=0`
- `escalated_unresolved=1`
- `overdue_not_escalated=1`

这表示当前 shared-dev `142` 的稳定观察面已经不再是 first-run 当天的 `after-escalate=4 items` 状态，而是：

- `after-escalate + admin auto-assign`

## 产物

### precheck

- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-observation-precheck-20260419-rerun/OBSERVATION_PRECHECK.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-observation-precheck-20260419-rerun/observation_precheck.json`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-observation-precheck-20260419-rerun/summary_probe.json`

### 第一次 readonly rerun（旧基线比对失败）

- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly/OBSERVATION_RESULT.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly/OBSERVATION_DIFF.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly/OBSERVATION_EVAL.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly.tar.gz`

### 第二次 readonly rerun（重冻结后通过）

- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly-freeze/OBSERVATION_RESULT.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly-freeze/OBSERVATION_DIFF.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly-freeze/OBSERVATION_EVAL.md`
- `/tmp/yuantus-shared-dev-rerun-20260419/tmp/p2-shared-dev-observation-20260419-rerun-readonly-freeze.tar.gz`

## 结论

- 最新主线 `5565c95` 下，shared-dev 观察工具链仍可用：
  - `precheck` 通过
  - `verify/render/compare/evaluate` 全可执行
- 第一次 readonly 失败不是代码回归，而是旧 frozen baseline 没包含后续 `admin auto-assign` 写入
- 当前 shared-dev `142` 已重新冻结到新的稳定基线：
  - `pending=2`
  - `overdue=3`
  - `escalated=1`
  - `items=5`
- 后续所有 readonly rerun，都应以上述 `5 items` 状态为基线，直到下一次明确允许的写操作再次改变环境
