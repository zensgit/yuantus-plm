# P2 Shared-dev 142 Readonly Refreeze Candidate Checklist

日期：2026-04-20

## 目的

当 `shared-dev 142` 的 `refreeze-readiness` 因为 future-deadline pending approval 失败时，
先生成一版 **stable readonly candidate**，评估“排除时间敏感 pending 项之后”的候选 baseline 是否值得采纳。

这份清单不直接刷新 tracked baseline。

## 快速入口

优先直接用：

```bash
bash scripts/run_p2_shared_dev_142_refreeze_candidate.sh
```

如果只想先看展开命令：

```bash
bash scripts/print_p2_shared_dev_142_refreeze_candidate_commands.sh
```

## 固定输入

- observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`
- current official readonly baseline:
  - `./artifacts/p2-observation/shared-dev-142-readonly-20260419`
- source current result:
  - `current/*` from the nested readonly rerun

## 最小证据包

至少保留：

- `current/OBSERVATION_RESULT.md`
- `STABLE_READONLY_CANDIDATE.md`
- `stable_readonly_candidate.json`
- `candidate/summary.json`
- `candidate/items.json`
- `candidate/anomalies.json`
- `candidate/export.json`
- `candidate/export.csv`
- `candidate/OBSERVATION_RESULT.md`
- `candidate/OBSERVATION_EVAL.md`

## 判断标准

### 候选包可用

- `CANDIDATE_READY=1`
- `CANDIDATE_DECISION_KIND=overdue-only-stable-candidate`
- `candidate/pending_count=0`

### 候选包不可用

- `CANDIDATE_READY=0`
- `CANDIDATE_DECISION_KIND=candidate-still-unstable`

## 下一步

如果候选包可用：

- 审查 `excluded_pending_items`
- 确认你们是否接受 “tracked readonly baseline 不再包含 future-deadline pending 项” 这条设计
- 接受后，再单独走新的 readonly refreeze / baseline switch 决策

如果候选包不可用：

- 继续等待 live state 稳定
- 或重新调查 drift / baseline 设计
