# P2 Shared-dev 142 Drift Investigation Checklist

日期：2026-04-20

## 目的

这份清单用于在 `142` 的 readonly baseline 已经发生漂移后，固定一轮**证据采集**，再决定：

- 继续查 drift 根因
- 或接受 drift 后再做 readonly refreeze

它不做任何 baseline refresh，也不应该替代 drift-audit。

## 什么时候用

当你已经遇到下面任一情况时，直接用这份 investigation 入口：

- `shared-dev-142-readonly-guard` 返回 `FAIL`
- `readonly-rerun` 返回 `FAIL`
- `drift-audit` 已经确认有漂移，但你还不准备马上 refreeze

## 快速入口

优先直接用：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation
```

如果只想先看展开命令：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-investigation-commands
```

## 固定输入

- observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`
- official readonly baseline:
  - `./tmp/p2-shared-dev-observation-20260421-stable`
- baseline label:
  - `shared-dev-142-readonly-20260421`
- baseline policy:
  - `overdue-only-stable`

## 最小执行顺序

### 1. 校验 env

```bash
scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"
```

### 2. 跑 investigation helper

```bash
bash scripts/run_p2_shared_dev_142_drift_investigation.sh
```

默认会生成：

- `./tmp/p2-shared-dev-142-drift-investigation-<timestamp>/drift-audit`
- `./tmp/p2-shared-dev-142-drift-investigation-<timestamp>/DRIFT_INVESTIGATION.md`
- `./tmp/p2-shared-dev-142-drift-investigation-<timestamp>/drift_investigation.json`
- `./tmp/p2-shared-dev-142-drift-investigation-<timestamp>.tar.gz`

## 最小证据包

至少保留：

- `drift-audit/DRIFT_AUDIT.md`
- `drift-audit/drift_audit.json`
- `DRIFT_INVESTIGATION.md`
- `drift_investigation.json`
- `drift-audit/current/OBSERVATION_RESULT.md`
- `drift-audit/current/OBSERVATION_DIFF.md`
- `drift-audit/current/OBSERVATION_EVAL.md`
- `drift-audit/current/STABLE_CURRENT_TRANSFORM.md`
- `drift-audit/current/stable_current_transform.json`
- `drift-audit/current/summary.json`
- `drift-audit/current/items.json`
- `drift-audit/current/anomalies.json`
- `drift-audit/current/export.json`
- `drift-audit/current/export.csv`
- `drift-audit/current/raw-current/OBSERVATION_RESULT.md`

## 先看什么

优先只看三件事：

1. `DRIFT_INVESTIGATION.md`
2. `drift-audit/DRIFT_AUDIT.md`
3. `drift-audit/current/OBSERVATION_EVAL.md`

如果三者共同显示：

- approval id 没变
- 但 `pending / overdue / anomalies` 变了

先看 `DRIFT_INVESTIGATION.md` 里的 `Likely Cause`：

- 如果是 `deadline-rollover`
  - 就按 **time-drift** 处理
  - 先确认没人带 `RUN_WRITE_SMOKE=1` 跑过
  - 再判断是不是 readonly baseline 本身已经过期
- 如果没有明确 `Likely Cause`
  - 再按 **state-drift** 处理
  - 优先排查状态推进来源，不要直接 refreeze。

## 候选写入来源

先查这几类：

- `src/yuantus/meta_engine/web/eco_router.py`
  - `POST /api/v1/eco/{eco_id}/auto-assign-approvers`
  - `POST /api/v1/eco/approvals/escalate-overdue`
- `src/yuantus/meta_engine/services/eco_service.py`
  - `auto_assign_stage_approvers()`
  - `escalate_overdue_approvals()`
- `scripts/verify_p2_dev_observation_startup.sh`
  - 是否有人带 `RUN_WRITE_SMOKE=1` 跑过
- `scripts/seed_p2_observation_fixtures.py`
  - 当前 drift 是否只是偏离了 fixture 预期

## 决策

如果 investigation 结论是：

- drift 能被预期写操作解释

则下一步进入 readonly refreeze：

- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_20260419.md`

如果 investigation 结论是：

- drift 能被 `deadline-rollover` 解释

则先判断这是不是一个应接受的时间敏感 baseline：

- 如果接受，就进入 readonly refreeze
- 如果不接受，就应该回头把 baseline 设计成非时间敏感样本

如果 investigation 结论是：

- drift 还解释不清
- 或看起来是非预期写入

则先停在 investigation，不做 baseline refresh。
