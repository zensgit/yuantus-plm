# DEV / Verification - Shared-dev 142 Top-Level Discoverability

日期：2026-04-20
仓库基线：`f5ff0fe`（`scripts: add shared-dev 142 entrypoint selector (#277)`）

## 目标

把 shared-dev `142` selector 从“脚本层已存在”补到“顶层入口也能直接发现”。

上一轮之后，`scripts/run_p2_shared_dev_142_entrypoint.sh` 已经是统一模式入口，但操作者在两个顶层面上仍然容易走偏：

- `README.md` 只暴露了 shared-dev rerun 文档，没有直接把 `142` selector 提到顶层
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md` 是冻结远端 `local-dev-env` 的 runbook，但没有明确把 official shared-dev `142` 重定向到 selector

## 实现

### 1. README 顶层 shared-dev 入口补齐 selector

在 `README.md` 的 shared-dev rerun 说明里补了：

- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --help`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-readonly-commands`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-probe`
- `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check`

这样操作者从仓库首页就能知道：

- shared-dev rerun 的总入口文档是什么
- 如果目标是 official shared-dev `142` readonly baseline，应该先看 selector，而不是先记底层 wrapper 名字

### 2. Remote runbook 明确边界

在 `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md` 新增“边界”段：

- 这份 runbook 只对应冻结的远端 `local-dev-env`
- 如果目标是 official shared-dev `142` readonly baseline，改走：
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --help`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-readonly-commands`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-probe`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check`
  - `docs/P2_ONE_PAGE_DEV_GUIDE.md`

这一步避免 remote-local-dev-env 和 official shared-dev `142` 两条线继续混用。

### 3. 补契约，防止顶层入口回退

新增/扩展 contract tests，锁住三类可见性：

- `README.md` 顶层 shared-dev 段必须暴露 `142` selector
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md` 必须把 official shared-dev `142` 指回 selector
- `docs/DEV_AND_VERIFICATION_SHARED_DEV_142_ENTRYPOINT_SELECTOR_20260420.md` 必须保留四个 mode 与 `--dry-run`

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## 结果

本轮没有新增执行能力，只补 discoverability。

补完之后：

- README 首页能直接把 shared-dev `142` 操作者导向统一 selector
- remote runbook 不再和 official shared-dev `142` baseline 入口混淆
- selector 自身的开发验证文档也被 contract test 锁住，不会悄悄丢 mode 或 `--dry-run`
