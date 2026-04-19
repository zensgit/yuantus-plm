# DEV & VERIFICATION - Shared-dev Stack Contracts Remediation - 2026-04-19

## Scope

在 `#255-#260` 这条 shared-dev bootstrap 栈继续推进时，所有 PR 的 `contracts` job 都卡在同一条 contract：

- `test_all_dev_and_verification_docs_are_indexed_in_delivery_doc_index_section`

根因不是业务代码，而是每条分支新增的 `docs/DEV_AND_VERIFICATION_*.md` 没同步写入：

- `docs/DELIVERY_DOC_INDEX.md`
- `## Development & Verification`

## Development

### Root cause

共享问题按栈分布如下：

- `#255`
  - `DEV_AND_VERIFICATION_SHARED_DEV_BOOTSTRAP_DOCKER_20260419.md`
- `#256`
  - `DEV_AND_VERIFICATION_SHARED_DEV_P2_OBSERVATION_BOOTSTRAP_E2E_20260419.md`
- `#257`
  - `DEV_AND_VERIFICATION_SHARED_DEV_BOOTSTRAP_HANDOFF_20260419.md`
- `#258`
  - `DEV_AND_VERIFICATION_SHARED_DEV_BOOTSTRAP_ENV_HELPER_20260419.md`
- `#259`
  - `DEV_AND_VERIFICATION_SHARED_DEV_BOOTSTRAP_ENV_VALIDATION_20260419.md`
- `#260`
  - `DEV_AND_VERIFICATION_SHARED_DEV_FIRST_RUN_CHECKLIST_20260419.md`

### Fixes applied

分别在对应 worktree / branch 上补了 `docs/DELIVERY_DOC_INDEX.md`：

- `/tmp/yuantus-shared-dev-bootstrap`
- `/tmp/yuantus-p2-observation-bootstrap`
- `/tmp/yuantus-bootstrap-handoff`
- `/tmp/yuantus-shared-dev-env-helper-index`
- `/tmp/yuantus-shared-dev-env-validate-index`
- `/tmp/yuantus-bootstrap-env-helper`

对应提交：

- `545114c` `docs(index): register shared-dev bootstrap verification`
- `9f7365c` `docs(index): register shared-dev bootstrap e2e docs`
- `22cf7fd` `docs(index): register shared-dev bootstrap handoff docs`
- `574498e` `docs(index): register shared-dev env helper docs`
- `fc0bf87` `docs(index): register shared-dev env validation docs`

另外顶层 `#260` 继续在 rebased base 上补齐：

- `DEV_AND_VERIFICATION_SHARED_DEV_FIRST_RUN_CHECKLIST_20260419.md`
- 本文档自身

## Verification

对 `#255-#259` 的各自 worktree，统一跑最小 contract 子集：

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

结果：

- `/tmp/yuantus-shared-dev-bootstrap` -> `2 passed`
- `/tmp/yuantus-p2-observation-bootstrap` -> `2 passed`
- `/tmp/yuantus-bootstrap-handoff` -> `2 passed`
- `/tmp/yuantus-shared-dev-env-helper-index` -> `2 passed`
- `/tmp/yuantus-shared-dev-env-validate-index` -> `2 passed`

顶层 `#260` 在吃进更新后的 `#259` 后，也应继续通过同一组 index contract。

## Result

这轮之后，shared-dev bootstrap 栈的主阻塞从：

- `contracts` index completeness failure

回到：

- 正常的 stacked PR 审核 / merge 顺序

也就是当前这条线不再被“文档索引漏登记”反复卡住。
