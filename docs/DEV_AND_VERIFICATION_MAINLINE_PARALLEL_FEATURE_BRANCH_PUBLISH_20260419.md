# Mainline Parallel Feature Branch Publish

日期：2026-04-19
主仓：`/Users/chouhua/Downloads/Github/Yuantus`
目标工位：`/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`

## 目标

把已经切好的本地 mainline follow-up feature branch 发布到 `origin`，建立可恢复的 upstream 跟踪面，避免后续会话或跨机器协作时只能依赖本地 worktree 状态。

## 背景

上一轮已经完成：

- 创建 clean baseline worktree：
  - `baseline/mainline-20260419-190340`
- 从 baseline 切出本地开发分支：
  - `feature/mainline-parallel-followup-20260419`

但当时该 `feature/*` 分支还只存在于本地 worktree 中。  
如果后续需要在其他终端、其他 clone，或新的回归会话里继续同一条开发线，最好先把它发布到 `origin` 并建立 upstream。

## 实际执行

### 1. 发布前确认

发布前确认：

- 当前 worktree：
  - `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`
- 当前本地开发分支：
  - `feature/mainline-parallel-followup-20260419`
- 与 `origin/main` 偏差：
  - `0 0`
- 同名远端分支在发布前不存在

### 2. 发布 feature branch 并建立 upstream

执行：

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340 \
  push -u origin feature/mainline-parallel-followup-20260419
```

### 3. 发布后验证

验证 1：本地分支已建立 upstream 跟踪

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340 \
  branch -vv --list feature/mainline-parallel-followup-20260419 baseline/mainline-20260419-190340
```

结果：

```text
  baseline/mainline-20260419-190340           b471afc [origin/main] docs(scripts): bootstrap mainline feature branch (#269)
* feature/mainline-parallel-followup-20260419 b471afc [origin/feature/mainline-parallel-followup-20260419] docs(scripts): bootstrap mainline feature branch (#269)
```

验证 2：远端同名分支已可见

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340 \
  ls-remote --heads origin feature/mainline-parallel-followup-20260419
```

结果：

```text
b471afc9f6d5655774defa93cab999f8a8eaa0c4	refs/heads/feature/mainline-parallel-followup-20260419
```

验证 3：发布时 `feature/*` 与 `origin/main` 仍是同一点位

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340 \
  rev-list --left-right --count feature/mainline-parallel-followup-20260419...origin/main
```

结果：

```text
0	0
```

## 结果

当前 mainline 并行开发面已经具备：

- 干净基线分支：
  - `baseline/mainline-20260419-190340`
- 可写本地开发分支：
  - `feature/mainline-parallel-followup-20260419`
- 对应远端恢复点：
  - `origin/feature/mainline-parallel-followup-20260419`

这意味着后续即使脱离当前 shell，也可以在任意 clone 中直接恢复到同一条 feature 开发线，而不需要重新手工命名或重新切分支。

## 说明

本轮没有再新增 bootstrap helper。原因是：

- 现有 canonical helper 已经存在：
  - `scripts/print_mainline_baseline_switch_commands.sh`
- 现有正式 runbook 已经覆盖从 baseline 切 topic branch 的动作：
  - `docs/RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md`

因此这次收口只补“发布到远端”这一步，而不重复制造新的 helper 面。

## 结论

- `feature/mainline-parallel-followup-20260419` 已经从“仅本地 worktree 可见”推进到“本地 + 远端都可恢复”
- 后续真实开发提交应继续落在 `feature/mainline-parallel-followup-20260419`
- `baseline/mainline-20260419-190340` 继续保留为只读干净基线，不应直接承载开发提交
