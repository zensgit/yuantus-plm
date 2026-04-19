# DEV / Verification - Shared-dev 142 Readonly One-Command Wrapper

日期：2026-04-19
仓库基线：`9211b64`（`Merge pull request #273 from zensgit/docs/shared-dev-142-readonly-baseline-entrypoint-20260419`）

## 目标

把 `142` 当前 official readonly baseline 从“固定 print helper”继续收口成“固定一条可执行 wrapper”。

本轮目标很具体：

1. 不再要求操作者复制三段命令
2. 不再要求操作者自己先恢复 canonical baseline 目录
3. 保持固定 baseline token、固定 readonly compare/eval 语义

## 背景

上一轮已经新增：

- `scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`

它解决了“不要手工猜 `BASELINE_DIR`”的问题，但仍然保留了一个明显的操作摩擦：

- 操作者仍要复制粘贴 `validate -> precheck -> run`

这意味着 142 的 readonly rerun 虽然已经“可查”，但还没有“可直接执行”。

## 实现

### 1. 新增单命令 wrapper

新增：

- `scripts/run_p2_shared_dev_142_readonly_rerun.sh`

默认固定：

- env file:
  - `$HOME/.config/yuantus/p2-shared-dev.env`
- baseline dir:
  - `./tmp/p2-shared-dev-observation-20260419-193242`
- baseline archive:
  - `./tmp/p2-shared-dev-observation-20260419-193242.tar.gz`
- baseline label:
  - `shared-dev-142-readonly-20260419`
- compare/eval mode:
  - `readonly`

执行顺序固定为：

1. `validate_p2_shared_dev_env.sh`
2. baseline 缺失时自动从 canonical `.tar.gz` 恢复
3. `precheck_p2_observation_regression.sh`
4. `run_p2_observation_regression.sh`

### 2. 保留可控开关

wrapper 只加最小必要参数：

- `--env-file`
- `--output-dir`
- `--baseline-dir`
- `--baseline-archive`
- `--baseline-label`
- `--skip-precheck`
- `--no-restore`
- `--no-archive`

控制原则：

- 默认走官方 142 baseline
- 只有在操作者明确知道自己在改什么时才 override

### 3. 更新入口文档

同步把以下入口改成优先指向新的单命令 wrapper：

- `scripts/print_p2_shared_dev_mode_selection.sh`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

同时保留旧的 print helper，用于：

- 审命令
- 调试
- 手工改局部参数

### 4. 补契约

同步更新：

- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

新增约束包括：

- runner 必须出现在交付脚本索引
- runner 必须进入 shared-dev observation script presence contract
- runner `--help` 必须继续使用 repo-safe env file 示例
- runner 必须锁定当前 official 142 baseline token

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

以及：

```bash
bash scripts/run_p2_shared_dev_142_readonly_rerun.sh --help
bash scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh | sed -n '1,80p'
```

验证点：

- 新 runner 脚本语法正常
- 新 runner 可被交付索引和 discoverability 契约发现
- `--help` 继续使用仓库外 env file 路径
- 142 official baseline 的 dir/archive/label 仍被固定锁定
- `DELIVERY_DOC_INDEX.md` 继续满足完整性和排序契约

## 结果

本轮后，shared-dev 142 的 readonly rerun 入口分成两层：

1. 默认执行：
   - `bash scripts/run_p2_shared_dev_142_readonly_rerun.sh`
2. 需要看展开命令时：
   - `bash scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`

也就是说，这条链已经从：

- 文档查找
- 手工拼参数
- 手工恢复 baseline
- 手工复制多段命令

收敛为：

- 单条 wrapper 默认执行
- print helper 只做解释和排障
