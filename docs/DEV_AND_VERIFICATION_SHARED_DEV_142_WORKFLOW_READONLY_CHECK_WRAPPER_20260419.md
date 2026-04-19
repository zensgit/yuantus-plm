# DEV / Verification - Shared-dev 142 Workflow Readonly Check Wrapper

日期：2026-04-19
仓库基线：`c9897ea`（`Merge pull request #275 from zensgit/scripts/shared-dev-142-workflow-probe-wrapper-20260419`）

## 目标

补齐 shared-dev `142` 观察链里最后一段仍然手工的步骤：

- 现在已经有：
  - `scripts/run_p2_shared_dev_142_workflow_probe.sh`
- 但 probe 跑完后，如果还要和 official frozen baseline 做正式 readonly compare/eval，操作者仍然要手工再跑：
  - `scripts/compare_p2_observation_results.py`
  - `scripts/evaluate_p2_observation_results.py`

本轮目标就是把这段再收成固定 wrapper。

## 问题

在 `142 workflow probe` 路径里，当前事实是：

1. GitHub Actions 侧只能做 `current-only`
2. official frozen baseline 在操作者本地
3. 所以“workflow probe 成功”不等于“对 frozen baseline 无漂移”

也就是说，少的不是 probe，而是：

- 下载 artifact 之后的本地 readonly compare/eval

## 实现

### 1. 新增固定 wrapper

新增：

- `scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`

它固定使用：

- workflow probe:
  - `scripts/run_p2_shared_dev_142_workflow_probe.sh`
- baseline dir:
  - `./tmp/p2-shared-dev-observation-20260419-193242`
- baseline archive:
  - `./tmp/p2-shared-dev-observation-20260419-193242.tar.gz`
- baseline label:
  - `shared-dev-142-readonly-20260419`
- current label:
  - `workflow-probe-current`

执行顺序固定为：

1. 先跑 `142 workflow probe`
2. 再把下载的 artifact 和 official baseline 做 `readonly` compare
3. 再做 `readonly` evaluate

### 2. 额外产物

除了 workflow probe 原有产物外，新 wrapper 额外写：

- `WORKFLOW_READONLY_DIFF.md`
- `WORKFLOW_READONLY_EVAL.md`
- `WORKFLOW_READONLY_CHECK.md`

其中：

- `WORKFLOW_READONLY_DIFF.md` 用于看冻结基线和 workflow artifact 的差异
- `WORKFLOW_READONLY_EVAL.md` 给出 readonly PASS / FAIL
- `WORKFLOW_READONLY_CHECK.md` 给出本轮最小导航页

### 3. 边界保持清楚

本轮没有把 `workflow probe` 和 `local readonly rerun` 混成一个脚本。

仍然保留三条入口：

1. 只要 workflow current-only probe：
   - `bash scripts/run_p2_shared_dev_142_workflow_probe.sh`
2. 要 workflow 路径 + official baseline readonly check：
   - `bash scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`
3. 要直接本地 hitting API 的 readonly rerun：
   - `bash scripts/run_p2_shared_dev_142_readonly_rerun.sh`

### 4. 文档与契约

同步更新：

- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py`

并在已有 fake-`gh` 行为测试文件里补了一条真实执行测试：

- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py`

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
bash scripts/run_p2_shared_dev_142_workflow_readonly_check.sh --help
```

验证点：

- 新 wrapper 脚本语法和 help 正常
- discoverability / 脚本索引能发现新 wrapper
- workflow dispatch 文档现在区分：
  - current-only probe
  - workflow + readonly check
  - direct local readonly rerun
- fake-`gh` 行为测试证明 wrapper 确实会：
  - 先跑 workflow probe
  - 再对下载的 artifact 做 readonly compare/eval
- `WORKFLOW_READONLY_EVAL.md` 在匹配基线时返回 `PASS`

## 结果

本轮后，`142` 的 workflow 路径也不再停在“下载 artifact 为止”。

它已经收敛为两条明确路径：

1. 最快 probe：
   - `bash scripts/run_p2_shared_dev_142_workflow_probe.sh`
2. 真正对官方 frozen baseline 做 workflow-route readonly 校验：
   - `bash scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`
