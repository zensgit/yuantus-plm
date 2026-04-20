# P2 Shared-dev 142 Readonly Refreeze Readiness Checklist

日期：2026-04-20

## 目的

在执行 `shared-dev 142` readonly refreeze 之前，先判断当前结果是否适合被冻结成新的 tracked baseline。

这份清单只回答一个问题：

- **现在适不适合 refreeze**

它不会直接刷新 baseline。

## 快速入口

优先直接用：

```bash
bash scripts/run_p2_shared_dev_142_refreeze_readiness.sh
```

如果只想先看展开命令：

```bash
bash scripts/print_p2_shared_dev_142_refreeze_readiness_commands.sh
```

## 固定输入

- observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`
- current official readonly baseline:
  - `./artifacts/p2-observation/shared-dev-142-readonly-20260419`

## 最小证据包

至少保留：

- `current/OBSERVATION_RESULT.md`
- `current/OBSERVATION_DIFF.md`
- `current/OBSERVATION_EVAL.md`
- `current/summary.json`
- `current/items.json`
- `current/anomalies.json`
- `REFREEZE_READINESS.md`
- `refreeze_readiness.json`

## 判断标准

### 可以 refreeze

- `REFREEZE_READY=1`
- `REFREEZE_DECISION_KIND=stable-readonly`
- 当前结果里没有 future-deadline pending approval

### 不要 refreeze

- `REFREEZE_READY=0`
- `REFREEZE_DECISION_KIND=future-deadline-pending`

这说明当前 shared-dev `142` 还带着会自然老化的 pending 样本。
如果此时强行 refreeze，新的 tracked baseline 也会很快再次 drift。

## 下一步

如果 readiness 通过：

- 再进入 readonly refreeze 流程

如果 readiness 不通过：

- 不要刷新 tracked baseline
- 先等待未来 deadline 跨过
- 或把 baseline 设计成不包含时间敏感 pending 项
