# Mainline Parallel Worktree Bootstrap

日期：2026-04-19
仓库：`/Users/chouhua/Downloads/Github/Yuantus`
主线基线：`57cb363`

## 目标

在主仓已经安全同步到最新 `origin/main` 后，继续按建议落地一个新的并行开发工位，使后续实现工作不再回到主仓本体进行。

## 背景

当前主仓虽然已经对齐主线，但仍保留两类本地未跟踪目录：

- `.claude/`
- `local-dev-env/`

这两个目录都不适合成为后续功能开发的直接写入面。  
因此本轮继续执行“从当前 `main` 拉出 clean mainline worktree”这条建议。

## 实际执行

### 1. 确认主仓已是最新主线

执行前确认：

- `HEAD = origin/main = 57cb363`
- 主仓状态只剩：
  - `?? .claude/`
  - `?? local-dev-env/`

### 2. 新建并行 worktree

实际创建：

- 路径：
  - `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`
- 分支：
  - `baseline/mainline-20260419-190340`
- 来源：
  - `origin/main`

执行命令：

```bash
git worktree add -b baseline/mainline-20260419-190340 \
  /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340 \
  origin/main
```

### 3. 创建后验证

在新 worktree 中确认：

- `git status --short --branch`
- `git rev-list --left-right --count HEAD...origin/main`

结果：

- 分支状态：
  - `## baseline/mainline-20260419-190340...origin/main`
- 主线差异计数：
  - `0 0`

说明：

- 新工位从最新主线起步
- 没有携带主仓中的 `.claude/` 或 `local-dev-env/` 未跟踪目录
- 可以直接作为后续并行开发的 clean baseline

## 同步修正

为了让这个建议后续可以直接复用，而不是继续靠人工口头说明，本轮同时修正了 mainline baseline switch helper：

- `scripts/print_mainline_baseline_switch_commands.sh`
- `docs/RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md`

修正内容：

- helper 新增 `--worktree-branch`
- 默认建议分支改为：
  - `baseline/mainline-<stamp>`
- 生成的 worktree 命令改为 branch-backed 形式，而不是 detached worktree

## 结果

本轮新增的并行开发工位为：

- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260419-190340`

建议后续开发方式：

- 主仓继续只承担同步 / 汇总 / 文档收口
- 新实现工作优先在该 clean mainline worktree 上展开
- 如果需要再分专题，可在该工位内继续创建 feature 分支，而不是回到主仓本体直接写
