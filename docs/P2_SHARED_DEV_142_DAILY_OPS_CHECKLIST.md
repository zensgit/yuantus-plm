# P2 Shared-dev 142 Daily Ops Checklist

日期：2026-04-21

## 目的

这份清单只覆盖 `142` 这台真实 shared-dev 在**维护态**下的最小日常操作路径。

它不再解释 bootstrap、proposal、refreeze 设计，只固定一条值班/维护用决策树：

1. 先跑 official readonly rerun
2. 如果失败，再跑 drift audit
3. 如果仍然需要解释，再跑 drift investigation

## 适用范围

适用于：

- `142` 已经是当前官方 readonly baseline 承载环境
- 你只想确认今天还能不能继续把它当稳定 shared-dev 使用
- 你需要先做值班判断，而不是立刻改 baseline

不适用于：

- fresh shared-dev first-run
- 重新 bootstrap `142`
- 直接做 refreeze / candidate / proposal

## 固定入口

推荐先看单入口命令单：

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-daily-commands
```

等价的直接打印脚本：

```bash
bash scripts/print_p2_shared_dev_142_daily_ops_commands.sh
```

## 最小执行顺序

### 1. 先跑 official readonly rerun

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
```

通过标准：

- `SUMMARY_HTTP_STATUS=200`
- readonly compare/eval `PASS`

如果这一步是绿的，今天的日常值班就到这里，可以继续把 `142` 当稳定 shared-dev 使用。

### 2. 如果 readonly rerun 失败，再跑 drift audit

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit
```

这一步的目标不是立刻修，而是先判断：

- 是不是指标真的变了
- approval 集合有没有变化
- 是不是单纯时间漂移 / deadline 老化

### 3. 如果 drift audit 仍不够解释，再跑 drift investigation

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation
```

这一步会固定一轮 evidence pack，用于区分：

- time drift / deadline rollover
- state drift
- 更可能的写入/任务来源

## 日常值班的停止线

出现以下任一情况，就不要继续走 refreeze，而是先停在 investigation 结果上：

- readonly rerun `FAIL`
- drift audit `FAIL`
- drift investigation 把本次变化归类为非预期 drift

## 日常值班不要做的事

正常 daily ops 场景下，不要直接跳到：

- `refreeze-readiness`
- `refreeze-candidate`
- `refreeze-proposal`
- `first-run bootstrap`

这些都属于变更 baseline 或重置环境的动作，不属于维护态快检。

## 相关文档

- `docs/P2_SHARED_DEV_142_RERUN_CHECKLIST.md`
- `docs/P2_SHARED_DEV_142_DRIFT_AUDIT_CHECKLIST.md`
- `docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
