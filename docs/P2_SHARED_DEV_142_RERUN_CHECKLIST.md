# P2 Shared-dev 142 Rerun Checklist

日期：2026-04-19

## 目的

这份清单固定 `142` 这台真实 shared-dev 的**常规 observation rerun** 路径。

它适用于：

- `142` 已经完成过 fresh shared-dev first-run
- `admin / ops-viewer / p2-observation fixtures` 已存在
- 这次目标只是重复执行：
  - `precheck_p2_observation_regression.sh`
  - `run_p2_observation_regression.sh`

它不适用于：

- 第一次初始化 `142`
- 需要 reset / 重新 bootstrap fixtures 的情况

如果要重新初始化，请改走：

- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- `bash scripts/print_p2_shared_dev_first_run_commands.sh`

## 固定环境

- shared-dev host: `142.171.239.56`
- API base URL: `http://142.171.239.56:7910`
- 本地 observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`

## 前提

- 所有相对路径命令都从仓库根目录执行
- `$HOME/.config/yuantus/p2-shared-dev.env` 已存在并可用
- 这份 env 至少包含：
  - `BASE_URL="http://142.171.239.56:7910"`
  - `TENANT_ID="tenant-1"`
  - `ORG_ID="org-1"`
  - `TOKEN`，或 `USERNAME/PASSWORD`
  - `ENVIRONMENT="shared-dev"`

## 最小执行顺序

### 1. 先校验本地 env

```bash
scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"
```

### 2. 先跑 precheck

```bash
scripts/precheck_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

预期至少有：

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`

如果 precheck 不绿，不要继续 full regression。

### 3. 跑 canonical wrapper

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-observation-142-$(date +%Y%m%d-%H%M%S)" \
ARCHIVE_RESULT=1 \
scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

### 4. 最低回传物

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`
- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`
- `README.txt`
- `OBSERVATION_RESULT.md`
- `${OUTPUT_DIR}.tar.gz`

## 当前期望结果

`142` 当前不是 fresh baseline，而是已经完成过一次 escalation 的 shared-dev。

常规 rerun 预期接近：

- `pending_count = 1`
- `overdue_count = 3`
- `escalated_count = 1`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`

如果结果明显偏离，再去看：

- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md`
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`

## 快速入口

如果只想直接拿命令：

```bash
bash scripts/print_p2_shared_dev_142_rerun_commands.sh
```
