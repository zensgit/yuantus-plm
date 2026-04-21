# P2 Shared-dev 142 Readonly Refreeze Proposal Checklist

日期：2026-04-21

## 目的

当 `shared-dev 142` 的 `refreeze-candidate` 已经产出稳定候选包时，
再生成一版 **formal readonly refreeze proposal**，把后续 baseline switch 所需的候选产物和更新目标固定下来。

这份清单仍然不直接刷新 tracked baseline。

## 快速入口

优先直接用：

```bash
bash scripts/run_p2_shared_dev_142_refreeze_proposal.sh
```

如果只想先看展开命令：

```bash
bash scripts/print_p2_shared_dev_142_refreeze_proposal_commands.sh
```

## 前置条件

- `refreeze-candidate` 已通过：
  - `CANDIDATE_READY=1`
  - `CANDIDATE_DECISION_KIND=overdue-only-stable-candidate`
- 你接受“新 tracked readonly baseline 不包含 future-deadline pending 项”这条设计

## 最小证据包

至少保留：

- `candidate-preview/STABLE_READONLY_CANDIDATE.md`
- `candidate-preview/stable_readonly_candidate.json`
- `REFREEZE_PROPOSAL.md`
- `refreeze_proposal.json`
- `proposal/<proposed-label>/summary.json`
- `proposal/<proposed-label>/items.json`
- `proposal/<proposed-label>/anomalies.json`
- `proposal/<proposed-label>/export.json`
- `proposal/<proposed-label>/export.csv`
- `proposal/<proposed-label>/OBSERVATION_RESULT.md`
- `proposal/<proposed-label>/OBSERVATION_EVAL.md`

## 判断标准

### 提案可进入下一步

- `PROPOSAL_READY=1`
- `PROPOSAL_DECISION_KIND=proposal-ready`
- `proposal/<proposed-label>/pending_count=0`

### 暂不进入下一步

- `PROPOSAL_READY=0`
- `PROPOSAL_DECISION_KIND=candidate-not-ready`

## 下一步

如果提案可用：

- 审查 `excluded_pending_items`
- 审查 `update_targets`
- 再单独做 tracked baseline switch PR

如果提案不可用：

- 回到 `refreeze-candidate` 或 `drift-investigation`
- 不要刷新 tracked baseline
