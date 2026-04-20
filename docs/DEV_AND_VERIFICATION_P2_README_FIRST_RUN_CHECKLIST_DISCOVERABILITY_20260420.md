# DEV / Verification - P2 README First-run Checklist Discoverability

日期：2026-04-20
仓库基线：`24555b6`（`docs: align README runbooks with P2 operator docs (#280)`）

## 目标

把 `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md` 也补进 `README.md` 的 `## Runbooks`，让 P2 的 shared-dev 首次执行入口和常规 rerun 入口处在同一层。

上一轮之后，README runbooks 已经能直接看到：

- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

但 shared-dev first-run 仍然只在 README 顶部 shared-dev 段落里出现，没有进入 runbooks 层。

## 实现

### 1. README Runbooks 增加 first-run checklist

在 `README.md` 的 `## Runbooks` 段新增：

- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`

这样 README 的 P2 operator-facing 文档分成两类：

- first-run:
  - `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- rerun / observation:
  - `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
  - `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
  - `docs/P2_ONE_PAGE_DEV_GUIDE.md`
  - `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
  - `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

### 2. 补 discoverability contract

扩展 `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`：

- `README.md` 可发现的 P2 runbooks 必须包含 `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- `docs/DELIVERY_DOC_INDEX.md` 也必须继续包含 `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- 新增本次文档自己的 token contract，防止 first-run checklist 从 README runbooks 层掉回去

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

本轮没有新增执行能力，只补 README runbooks 的 first-run discoverability。

补完之后：

- README `## Runbooks` 同时覆盖 shared-dev first-run 和 shared-dev rerun 两条主线
- operator 不需要先回忆“first-run checklist 在 README 顶部还是 runbooks 里”
- 这条 first-run 入口已经进 discoverability contract，不会再静默回退
