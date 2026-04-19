# DEV / Verification - Shared-dev 142 Workflow Probe Wrapper

日期：2026-04-19
仓库基线：`1c5d59a`（`Merge pull request #274 from zensgit/scripts/shared-dev-142-readonly-one-command-wrapper-20260419`）

## 目标

补齐 shared-dev `142` 的最后一层固定入口：

- 本地 readonly compare/eval 已有：
  - `scripts/run_p2_shared_dev_142_readonly_rerun.sh`
- GitHub Actions current-only probe 仍只有通用 wrapper：
  - `scripts/run_p2_observation_regression_workflow.sh`

本轮目标是给 `142` 再加一条固定 workflow probe 入口，避免操作者每次重复传：

- `base_url`
- `tenant_id`
- `org_id`
- `environment`

## 设计边界

这条新入口只做：

- GitHub Actions `workflow_dispatch`
- artifact 下载
- `current-only` probe

它**不**做：

- readonly baseline compare
- frozen baseline evaluate

原因很直接：

- 现有 `p2-observation-regression` workflow 在 Actions 侧固定是 `EVAL_MODE=current-only`
- frozen baseline artifact 在操作者本地，不在 GitHub runner 侧

所以 `workflow probe` 和 `local readonly rerun` 必须继续分开。

## 实现

### 1. 新增固定 workflow probe wrapper

新增：

- `scripts/run_p2_shared_dev_142_workflow_probe.sh`

默认固定：

- `base_url=http://142.171.239.56:7910`
- `tenant_id=tenant-1`
- `org_id=org-1`
- `environment=shared-dev-142-workflow-probe`
- `ref=main`
- `username=admin`
- `out_dir=./tmp/p2-shared-dev-142-workflow-probe-<timestamp>`

内部直接调用：

- `scripts/run_p2_observation_regression_workflow.sh`

### 2. 更新入口文档

同步更新：

- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
- `scripts/print_p2_shared_dev_observation_commands.sh`

文档明确区分：

1. 只读正式回归：
   - `bash scripts/run_p2_shared_dev_142_readonly_rerun.sh`
2. GitHub Actions current-only probe：
   - `bash scripts/run_p2_shared_dev_142_workflow_probe.sh`

### 3. 契约与 CI

同步更新：

- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py`

并新增一条 fake-`gh` 行为测试到：

- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py`

同时把该测试文件加入：

- `.github/workflows/ci.yml`

这样脚本改动触发的 `contracts` job 就会真的执行 workflow wrapper 行为测试，而不只是字符串契约。

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

以及：

```bash
bash scripts/run_p2_shared_dev_142_workflow_probe.sh --help
```

验证点：

- 新 wrapper 脚本语法正常
- discoverability / 脚本索引能发现新 wrapper
- workflow dispatch 文档明确区分 current-only probe 和 local readonly rerun
- fake-`gh` 行为测试证明固定参数确实被转发到通用 workflow wrapper
- `.github/workflows/ci.yml` contracts 列表仍保持排序

## 结果

本轮后，shared-dev `142` 的观察入口分成三条，各自边界清楚：

1. 正式 readonly rerun：
   - `bash scripts/run_p2_shared_dev_142_readonly_rerun.sh`
2. GitHub Actions current-only probe：
   - `bash scripts/run_p2_shared_dev_142_workflow_probe.sh`
3. 需要审展开命令时：
   - `bash scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`

这样 `142` 的本地和 workflow 两条固定入口都收敛完成了。
