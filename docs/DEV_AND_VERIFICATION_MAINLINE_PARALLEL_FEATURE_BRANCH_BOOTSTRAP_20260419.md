# Mainline Parallel Feature Branch Bootstrap

日期：2026-04-19
主仓：`/Users/chouhua/Downloads/Github/Yuantus`
目标工位：`/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`

## 目标

把已经创建好的 clean baseline worktree 再推进一步，切出一个真正可开发的本地 topic 分支，而不是继续停留在 `baseline/mainline-*` 基线分支上。

## 背景

上一轮已经完成：

- 新建 clean mainline worktree
- 命名固定为：
  - worktree：`mainline-<stamp>`
  - branch：`baseline/mainline-<stamp>`

但这还只是“干净基线工位”。  
如果后续要真正开始开发，最安全的下一步不是直接在 `baseline/*` 上提交，而是先在该工位里切出一个独立的 `feature/*` 分支。

## 实际执行

### 1. 确认 baseline 工位干净

执行前确认：

- worktree：
  - `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`
- 当前分支：
  - `baseline/mainline-20260419-190340`
- 与 `origin/main` 偏差：
  - `0 0`

### 2. 切出本地 topic 分支

由于本轮用户没有指定更窄的实现主题，先创建一个中性的后续开发分支：

- `feature/mainline-parallel-followup-20260419`

执行：

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340 \
  switch -c feature/mainline-parallel-followup-20260419
```

### 3. 创建后验证

验证点：

- 新 worktree 当前分支已从 `baseline/mainline-20260419-190340` 切到：
  - `feature/mainline-parallel-followup-20260419`
- 原 `baseline/mainline-20260419-190340` 分支仍保留，作为干净基线参照
- 新分支创建时与 baseline 指向同一提交起点

## 同步修正

为避免这一步继续依赖人工口头建议，本轮同时补齐了 mainline baseline switch helper / runbook：

- `scripts/print_mainline_baseline_switch_commands.sh`
- `docs/RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md`

补齐内容：

- helper 新增：
  - `--topic-branch`
- 输出新增一段显式步骤：
  - 在 clean worktree 内执行 `git switch -c <topic-branch>`
- runbook 新增：
  - “Before editing, cut a real topic branch in the new worktree”
- 如果操作者已经知道下一条开发分支名，可以直接打印完整命令：
  - `bash scripts/print_mainline_baseline_switch_commands.sh --topic-branch ...`

## 结果

当前推荐的后续开发面为：

- 路径：
  - `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`
- 当前开发分支：
  - `feature/mainline-parallel-followup-20260419`

保留的干净基线分支为：

- `baseline/mainline-20260419-190340`

## 结论

- baseline worktree 已经从“只可作为参照”推进到“可直接开始开发”
- 后续提交不应落在 `baseline/mainline-*` 上，而应落在新切出的 `feature/*` 分支上
- `print_mainline_baseline_switch_commands.sh` 与 `RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md` 现在已经把这一步固化下来，后面可以直接复用
