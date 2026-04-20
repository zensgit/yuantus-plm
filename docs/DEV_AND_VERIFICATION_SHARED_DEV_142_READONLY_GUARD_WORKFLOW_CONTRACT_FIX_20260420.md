# DEV / Verification - Shared-dev 142 Readonly Guard Workflow Contract Fix

日期：2026-04-20

## 目标

修复 `origin/main` 上 `shared-dev-142-readonly-guard.yml` 违反仓库 workflow 契约的问题，使全仓 contracts 恢复为绿色。

## 背景

`feat(ops): add shared-dev 142 readonly guard workflow (#289)` 合入后，contracts job 失败在 3 条统一约束：

1. `concurrency.group` 没有使用仓库标准模板 `${{ github.workflow }}-${{ github.ref }}`
2. `concurrency.group` 不包含 `github.workflow`
3. `permissions.actions` 被设置为 `write`，但该 workflow 不在 actions-write allowlist 中

这会导致任何基于最新 `origin/main` 的 PR merge ref 都被 contracts job 阻断，包括与该 workflow 无关的 PR。

## 改动

文件：

- `.github/workflows/shared-dev-142-readonly-guard.yml`

变更：

- `permissions.actions: write` -> `read`
- `concurrency.group: shared-dev-142-readonly-guard` -> `${{ github.workflow }}-${{ github.ref }}`

未改：

- workflow 名称
- trigger
- steps
- artifact 行为
- readonly guard 业务逻辑

## 验证

执行：

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：

- `7 passed`

## 影响

- 修复的是 repo-wide workflow contracts，不是 shared-dev 业务逻辑。
- 这条修复是 main 基线卫生项，应该与 CAD backend profile PR 分开提交。
- 修完后，像 `#288` 这类无关 PR 才不会因为 `origin/main` 的 workflow 契约问题被误伤。

## 结论

这是一条最小、独立、可单独合并的基线修复。它的职责只是把 `shared-dev-142-readonly-guard.yml` 拉回仓库统一 workflow 契约。
