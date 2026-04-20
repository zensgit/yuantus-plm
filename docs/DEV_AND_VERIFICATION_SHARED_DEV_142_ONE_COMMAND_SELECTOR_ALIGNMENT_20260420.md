# DEV / Verification - Shared-dev 142 One-Command Selector Alignment

日期：2026-04-20
仓库基线：`b4eca58`（`docs: expose shared-dev 142 selector from top-level entrypoints (#278)`）

## 目标

把 `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md` 从“只露出 readonly 一条线”补到“完整对齐 shared-dev `142` selector 模式集”。

上一轮之后：

- `README.md` 已经露出 selector
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md` 已经明确把 official shared-dev `142` 指回 selector

剩下的缺口是：

- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md` 虽然已经用 selector，但还没把 `--help`、`workflow-probe`、`workflow-readonly-check` 这些模式显式写出来

## 实现

### 1. One-command 文档补齐 selector 模式集

在 `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md` 里补了：

- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --help`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-readonly-commands`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-probe`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check`

这样 operator 从 one-command 文档就能看全：

- 只做本地 readonly rerun 该走哪条
- 只想展开固定命令时该走哪条
- 只做 workflow current-only probe 该走哪条
- 要做 workflow + readonly compare/eval 该走哪条

### 2. 补 contract，锁住 one-command 对 selector 的对齐

扩展 `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py`：

- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md` 必须保留 `--help`
- 必须保留 `print-readonly-commands`
- 必须保留 `drift-audit`
- 必须保留 `workflow-probe`
- 必须保留 `workflow-readonly-check`

另外把本次文档：

- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_ONE_COMMAND_SELECTOR_ALIGNMENT_20260420.md`

也纳入同一个 contract matrix，避免后续这条对齐结论脱钩。

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## 结果

本轮没有新增执行能力，只做文档对齐和 contract 固化。

补完之后：

- one-command 文档与 shared-dev `142` selector 的完整模式集一致
- operator 不需要再从 one-command 页跳去猜 workflow 还是 readonly 入口
- 这条对齐关系已经进 contract，不会再静默回退成只露出单一 mode
