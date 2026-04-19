# Mainline Baseline Switch Helper Contracts

日期：2026-04-19
主仓：`/Users/chouhua/Downloads/Github/Yuantus`

## 目标

把 `scripts/print_mainline_baseline_switch_commands.sh` 从“已有 canonical helper 但缺少专门 CI 合同”的状态，收紧到和仓库中其他 `print_*` helper 一样的可回归约束面。

## 发现的实际缺口

在本轮检查里确认了两个问题：

1. helper 已经是正式入口，但还没有独立的 CI 合同测试
2. `--repo PATH` 选项虽然会切换打印出的目标仓路径，但 `current branch` 和默认 `backup branch` 仍然取自调用脚本的当前仓，而不是目标仓
3. `feature/*` 发布到 `origin` 并建立 upstream 这一步还只存在于执行记录里，没有进入正式 runbook/helper
4. helper 还没有进入 `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`，可发现性和同类 canonical helper 不一致

第二点会直接把生成的 `rev-list` / `branch backup/...` 模板带偏。  
第三点则会让操作者停在“本地 clean worktree 已切 topic branch”这一半流程，而缺少“让分支可跨会话恢复”的 canonical 动作。

## 本轮修正

### 1. 修正 helper 的 `--repo` 语义

文件：

- `scripts/print_mainline_baseline_switch_commands.sh`

修正内容：

- `CURRENT_BRANCH` 改为在参数解析后，基于 `REPO_PATH` 计算
- 默认 `BACKUP_BRANCH` 改为在参数解析后，基于目标仓当前分支生成
- 保留 `--backup-branch` 显式覆盖能力

这样当操作者传入其他仓路径时，helper 打印出的：

- `# current branch: ...`
- `# suggested backup branch: ...`
- `git rev-list ...`
- `git branch backup/...`

都会和目标仓一致。

### 2. 把 publish/upstream 提升为正式 workflow

更新：

- `scripts/print_mainline_baseline_switch_commands.sh`
- `docs/RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md`

补齐内容：

- 在 clean worktree 中切出 `feature/*` 分支之后，增加正式的：
  - `git push -u origin feature/<topic>-<YYYYMMDD>`
- runbook 明确把这一步定义为：
  - 让 clean worktree 分支在后续 shell / clone / 回归会话里可恢复
- helper 在传入 `--topic-branch` 时，会打印完整的 publish 命令

### 3. 补齐 helper 专门合同测试

新增：

- `src/yuantus/meta_engine/tests/test_ci_contracts_mainline_baseline_switch_helper.py`

覆盖点：

- `--help` 文本包含主要参数
- 默认输出仍包含 baseline worktree / topic branch / publish / rollback references
- 临时 git 仓场景下，`--repo` 会正确读取目标仓分支并生成默认 backup branch
- 当给定 `--topic-branch` 时，会打印 `push -u origin ...`
- runbook 与 README 仍保留 helper 的可发现入口

### 4. 纳入 shell syntax 固定名单

更新：

- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

补齐：

- `scripts/print_mainline_baseline_switch_commands.sh`

这样后续若 helper 出现 shell 语法损坏，也会在固定 CI 合同面上直接暴露。

### 5. 补齐交付脚本索引

更新：

- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

补齐：

- 脚本文件名条目：
  - `print_mainline_baseline_switch_commands.sh`
- 说明条目：
  - 该 helper 会打印 dirty feature worktree 保全、切到 `baseline/mainline-*`、切真实 `feature/*`、以及 `push -u origin ...` 的命令模板

这样 README/runbook 之外，交付脚本索引里也能直接发现这条 helper。

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_mainline_baseline_switch_helper.py \
  src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

结果：

- helper 合同测试通过
- shell syntax 固定名单通过
- workflow script reference 合同通过
- 本次新增开发及验证文档通过索引完整性/排序检查
- 总结果：
  - `19 passed`

## 结论

- `print_mainline_baseline_switch_commands.sh` 的 `--repo` 语义现在和目标仓一致
- `feature/*` publish/upstream 已经进入正式 runbook/helper，而不再只留在执行记录里
- mainline baseline switch helper 已经进入 CI 合同面和交付脚本索引，而不再只是“文档里提到”
- 后续如果 helper 输出漂移、参数说明丢失、或 shell 语法损坏，都能被固定测试直接拦住
