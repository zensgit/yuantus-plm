# DEV / Verification - P2 README Runbook Discoverability Alignment

日期：2026-04-20
仓库基线：`d43a561`（`docs: align one-command guide with shared-dev 142 selector (#279)`）

## 目标

把 P2 的 operator-facing 文档入口从“README 顶层零散出现”补到“README `## Runbooks` 里也能稳定发现”。

在上一轮之后：

- `README.md` 顶层 shared-dev 段已经能看到 selector
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md` 已经对齐到 shared-dev `142` selector 的完整模式集

剩下的缺口是：

- `README.md` 的 `## Runbooks` 里还没把 `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md` 和 `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md` 列为 operator 入口

## 实现

### 1. README Runbooks 补齐两个 P2 operator 入口

在 `README.md` 的 `## Runbooks` 段新增：

- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

这样 README 的 P2 runbook 面现在能直接看到：

- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

也就是把 one-command、workflow dispatch、one-page guide、remote runbook、shared-dev handoff 这五个日常 operator 文档放到同一入口层。

### 2. 补 discoverability contract

扩展 `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`：

- `README.md` `## Runbooks` 必须保留上述五个 P2 文档
- `docs/DELIVERY_DOC_INDEX.md` 也必须继续包含：
  - `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
  - `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- 新增本次文档自己的 token contract，防止 README runbooks 收口结论回退

## 验证

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## 结果

本轮没有新增执行能力，只补 README runbook 可见性。

补完之后：

- operator 从 README `## Runbooks` 就能直接找到 P2 one-command 和 shared-dev handoff
- P2 的五个常用执行文档已经在 README runbooks 层形成闭环
- 这条收口关系已经进 discoverability contract，不会再静默回退
