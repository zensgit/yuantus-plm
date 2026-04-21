# P2 Shared-dev 142 Drift Audit Checklist

日期：2026-04-20

## 目的

这份清单固定 `142` 这台真实 shared-dev 在 **readonly baseline 漂移** 时的排查路径。

它适用于：

- `shared-dev-142-readonly-guard` 返回 drift / readonly evaluation `FAIL`
- 本地 `readonly-rerun` 返回 drift / readonly evaluation `FAIL`
- 你需要在决定是否 refreeze 前，把 baseline/current 的关键差异固定成一个可回传的审计结果

它不适用于：

- 第一次初始化 `142`
- 常规 observation rerun
- 直接做 baseline refresh / refreeze

## 快速入口

优先直接用：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit
```

如果只想先看展开后的命令：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-drift-commands
```

## 固定环境

- shared-dev host: `142.171.239.56`
- API base URL: `http://142.171.239.56:7910`
- 本地 observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`
- 当前 official readonly baseline:
  - `./tmp/p2-shared-dev-observation-20260421-stable`
  - label: `shared-dev-142-readonly-20260421`
  - policy: `overdue-only-stable`

## 最小执行顺序

### 1. 先确认 env 可用

```bash
scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"
```

### 2. 跑 drift audit

```bash
bash scripts/run_p2_shared_dev_142_drift_audit.sh
```

默认会生成：

- `./tmp/p2-shared-dev-142-drift-audit-<timestamp>/current`
- `./tmp/p2-shared-dev-142-drift-audit-<timestamp>/current/raw-current`
- `./tmp/p2-shared-dev-142-drift-audit-<timestamp>/current-precheck`
- `./tmp/p2-shared-dev-142-drift-audit-<timestamp>/DRIFT_AUDIT.md`
- `./tmp/p2-shared-dev-142-drift-audit-<timestamp>/drift_audit.json`
- `./tmp/p2-shared-dev-142-drift-audit-<timestamp>.tar.gz`

### 3. 需要回传的最小结果

- `DRIFT_AUDIT.md`
- `drift_audit.json`
- `current/OBSERVATION_RESULT.md`
- `current/OBSERVATION_DIFF.md`
- `current/OBSERVATION_EVAL.md`
- `current/STABLE_CURRENT_TRANSFORM.md`
- `current/stable_current_transform.json`
- `current/summary.json`
- `current/anomalies.json`
- `current/raw-current/OBSERVATION_RESULT.md`
- `${OUTPUT_DIR}.tar.gz`

## 判断标准

如果 drift audit 结果显示：

- 只是预期中的状态推进
- 差异可以用既有写操作解释
- 没有新的异常计数失真

则下一步进入：

- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_20260419.md`

如果 drift audit 结果显示：

- 有未知 approval id 增减
- `pending / overdue / anomalies` 的变化无法由既有写操作解释
- 观测面本身可能已经异常

则下一步先做原因排查，不做 refreeze。

这一步优先固定 investigation evidence pack：

- `docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-investigation-commands`
- `bash scripts/run_p2_shared_dev_142_drift_investigation.sh`

预期额外产物：

- `DRIFT_INVESTIGATION.md`
- `drift_investigation.json`
