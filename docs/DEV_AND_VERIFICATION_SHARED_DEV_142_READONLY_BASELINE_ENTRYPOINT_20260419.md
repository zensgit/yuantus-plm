# DEV / Verification - Shared-dev 142 Readonly Baseline Entrypoint

日期：2026-04-19
仓库基线：`4390c64`（`Merge pull request #272 from zensgit/docs/shared-dev-142-observation-rerun-20260419`）

## 目标

把 `142` 当前 official readonly baseline 的 rerun 入口固化成固定 helper，避免后续操作者再手工回忆：

- 哪个 `BASELINE_DIR` 才是当前有效基线
- 哪个 `.tar.gz` 是对应归档
- `BASELINE_LABEL` / `EVAL_MODE` 应该怎么传

这次不改运行时逻辑，只收敛操作入口和契约。

## 问题

此前文档虽然已经明确 `142` 当前 readonly baseline 是：

- `./tmp/p2-shared-dev-observation-20260419-193242`

但实际执行时仍需要操作者自己在：

- runbook
- rerun doc
- `tmp/`

之间来回核对，然后手工拼出：

- `BASELINE_DIR`
- `BASELINE_LABEL`
- `EVAL_MODE=readonly`

这会带来两个稳定风险：

1. 误用旧的 `4 items` baseline
2. 每次 rerun 都重复做人工查找

## 实现

### 1. 新增固定 helper

新增脚本：

- `scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`

脚本直接固化以下内容：

- host:
  - `142.171.239.56`
- canonical baseline dir:
  - `./tmp/p2-shared-dev-observation-20260419-193242`
- canonical archive:
  - `./tmp/p2-shared-dev-observation-20260419-193242.tar.gz`
- baseline label:
  - `shared-dev-142-readonly-20260419`
- eval mode:
  - `readonly`

同时保留一个可控 override：

- `P2_SHARED_DEV_142_BASELINE_DIR`

只有在操作者明确把官方 baseline 解压或复制到别处时才需要设置。

### 2. 接入现有 handoff 入口

同步更新：

- `scripts/print_p2_shared_dev_mode_selection.sh`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`

让 shared-dev 142 的 readonly rerun 直接指向新 helper，而不是继续要求操作者手工找 `BASELINE_DIR`。

### 3. 补 discoverability / syntax 契约

同步更新：

- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

并新增一个专门测试，锁定 helper 中的关键 token：

- baseline dir
- baseline archive
- `BASELINE_LABEL`
- `EVAL_MODE`
- host `142.171.239.56`

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
bash scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh
```

验证点：

- 新 helper 脚本语法正常
- 交付脚本索引能发现新 helper
- `DELIVERY_DOC_INDEX.md` 仍满足完整性与排序契约
- 新 helper 输出的命令已固定到当前 official readonly baseline

## 结果

本轮后，`142` 的 readonly rerun 入口从“文档里查找 + 手工拼参数”收敛为“固定 helper + 固定 token”。

后续如果 `142` 的官方 readonly baseline 再次变化，需要做的就只有两件事：

1. 更新 helper 中的 canonical baseline token
2. 更新对应 DEV / Verification 文档与契约测试
