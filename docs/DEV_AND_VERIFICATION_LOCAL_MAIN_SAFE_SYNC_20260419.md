# Local Main Safe Sync

日期：2026-04-19
仓库：`/Users/chouhua/Downloads/Github/Yuantus`

## 目标

在不破坏本地未提交目录的前提下，把主仓 `main` 从落后状态安全并到最新 `origin/main`，并确认本地重叠文档改动已经被主线吸收，不需要手工重做。

## 初始状态

开始执行前，主仓状态为：

- `HEAD = efd79b8`
- `origin/main = 483825d`
- `main...origin/main [behind 4]`

本地工作树里与主线可能重叠的内容只有两项：

- 已跟踪修改：
  - `docs/DELIVERY_DOC_INDEX.md`
- 未跟踪文档：
  - `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md`

另外还存在两个不参与本轮并线的未跟踪目录：

- `.claude/`
- `local-dev-env/`

## 风险判断

这轮主线落后提交不是纯文档同步，其中：

- `#263` 把 `DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md` 合进主线
- `#264` 还修改了 `scripts/*`、`.github/workflows/ci.yml` 与一个 CI contract test
- `#266` 又补进了 readonly refreeze 文档和两处 runbook 说明

因此不能在有本地已跟踪修改的情况下，直接把这轮更新当成“无脑文档快进”。

## 实际执行

### 1. 先备份重叠路径

在任何清理动作之前，先把会被并线影响的本地内容备份到：

- `/tmp/yuantus-local-main-safe-sync-20260419`

备份内容：

- `/tmp/yuantus-local-main-safe-sync-20260419/DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md`
- `/tmp/yuantus-local-main-safe-sync-20260419/DELIVERY_DOC_INDEX.local.patch`
- `/tmp/yuantus-local-main-safe-sync-20260419/status.before.txt`

### 2. 确认本地文档与主线关系

结果：

- 备份的 `DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md` 与当前主线版本完全一致
- 校验：
  - `cmp` 结果：`IDENTICAL`
  - `sha256`：
    - `b243e2e62ed60d4d33a562507f2af11c6461c60de4b4159cb064193e6873b3d0`

说明：

- 这个未跟踪文档不是额外本地内容，而是已经被 `#263` 合进主线的同一份文件

对 `docs/DELIVERY_DOC_INDEX.md` 的判断是：

- 本地修改只补了 `SHARED_DEV_142_FIRST_RUN_EXECUTION` 一行
- 但最新主线已经同时包含：
  - `SHARED_DEV_142_FIRST_RUN_EXECUTION`
  - `SHARED_DEV_FIRST_RUN_BASE_COMPOSE`
  - `SHARED_DEV_142_READONLY_REFREEZE`

所以本地索引修改也是“已被主线覆盖但版本更旧”的状态。

### 3. 只清理重叠路径

本轮没有动 `.claude/` 与 `local-dev-env/`。

只对两条与主线重叠的路径做了最小清理：

- 删除未跟踪但已被主线吸收的：
  - `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md`
- 还原已跟踪但已被主线覆盖的：
  - `docs/DELIVERY_DOC_INDEX.md`

### 4. 安全快进主线

执行：

```bash
git pull --ff-only origin main
```

结果：

- `HEAD = 483825d`
- `git rev-list --left-right --count HEAD...origin/main`：
  - `0 0`

## 并线结果

当前主仓状态：

- 分支：
  - `docs/local-main-safe-sync-20260419`
- 基线：
  - `HEAD = origin/main = 483825d`
- 工作树：
  - 只剩未跟踪目录 `.claude/`、`local-dev-env/`

本轮主线同步进来的关键内容包括：

- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_FIRST_RUN_EXECUTION_20260419.md`
- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_20260419.md`
- `docs/DEV_AND_VERIFICATION_SHARED_DEV_FIRST_RUN_BASE_COMPOSE_20260419.md`
- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `scripts/generate_p2_shared_dev_bootstrap_env.sh`
- `scripts/print_p2_shared_dev_bootstrap_commands.sh`
- `scripts/print_p2_shared_dev_first_run_commands.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_shared_dev_first_run_base_compose.py`

## 结论

- 这次本地并线不需要手工合并或重复提交 `SHARED_DEV_142_FIRST_RUN_EXECUTION` 文档
- 本地 `DELIVERY_DOC_INDEX.md` 修改也不应保留，因为它落后于主线已合并版本
- 经过备份后，只清理重叠路径再执行 `ff-only pull` 是这轮的最小风险做法
- 后续如果再次遇到：
  - 本地已跟踪修改命中 `docs/DELIVERY_DOC_INDEX.md`
  - 或主线更新命中 `scripts/*` / `.github/workflows/*`

  仍应先备份或暂存，再做 `git pull --ff-only origin main`
