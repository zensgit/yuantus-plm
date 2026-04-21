# DEV_AND_VERIFICATION_PR309_NUMBERING_FLOOR_DB_PUSHDOWN_MERGE_20260421

## 1. 目标

闭环 `PR #309`（`perf: push down numbering floor query`）的主干落地过程：

- 确认 GitHub checks 收敛
- 合并到 `main`
- 同步本地主仓库
- 跑 merge 后 focused regression
- 记录本轮执行证据

本 PR 对应的是一个中等规模但边界明确的性能增量：

- `NumberingService._floor_allocated_value()` 对 `sqlite` / `postgresql` 改走 DB 聚合
- 非主方言保留 Python fallback
- `item_number` / `number` 双读兼容保持不变

## 2. Merge 前状态

GitHub 侧在执行 merge 前的观察：

- PR: `#309`
- title: `perf: push down numbering floor query`
- head: `a2ed61029dfe53c856320f89806d66bd0beefe26`
- changed files: `4`
- review blocker: `0`

Checks 初次运行时：

- `detect_changes (CI)` → SUCCESS
- `contracts` → SUCCESS
- `plugin-tests` → SUCCESS
- `regression` → SUCCESS
- `playwright-esign` → FAILURE

失败归因：

- 失败用例是 `playwright/tests/bom_obsolete_weight.spec.js`
- 失败点是 `POST /api/v1/bom/{item_id}/obsolete/resolve`
- 服务链落在 `bom_router.py` + `bom_obsolete_service.py`
- 日志核心错误是 `sqlite3.OperationalError: database is locked`

结论：

- 该失败不经过 `numbering_service.py`
- 与本 PR 的 numbering floor 下推改动面无直接交集
- 先按 flaky / 环境锁冲突处理，重跑 failed job 再判断

## 3. CI 收敛

执行：

```bash
gh run rerun 24699808306 --repo zensgit/yuantus-plm --failed
```

重跑后：

- `playwright-esign` → SUCCESS
- `mergeStateStatus` 从 `UNSTABLE` 收敛为 `CLEAN`
- 其余 checks 保持绿

结论：**可合**。

## 4. Merge 执行

执行：

```bash
gh pr merge 309 --repo zensgit/yuantus-plm --squash --delete-branch
```

结果：

- PR `#309` merged
- merge commit: `33be2b94e4b4e39c22df1ee4ce8f868d884c9d07`
- merged at: `2026-04-21T01:56:50Z`
- remote branch deleted

## 5. Post-merge 本地同步

执行：

```bash
git switch main
git pull --ff-only
```

结果：

- local `main` 从 `7225d63` 前进到 `33be2b9`
- working tree 只剩未跟踪的 `.claude/` 和 `local-dev-env/`

## 6. Post-merge 验证

### 6.1 Numbering focused regression

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/operations/tests/test_update_op.py
```

结果：`21 passed in 0.33s`

### 6.2 Doc-index contract tests

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：`3 passed in 0.02s`

## 7. 本轮结论

`PR #309` 已完成一条完整闭环：

1. DB 下推实现
2. 初次 CI 发现与改动面无关的 `sqlite database is locked`
3. failed-job rerun 收敛
4. squash merge 到 `main`
5. merge 后 focused regression 继续全绿

这说明 numbering floor 的主路径性能补丁已经稳定落地主干。

## 8. 产物

已在 `main` 的运行时代码与测试：

- `src/yuantus/meta_engine/services/numbering_service.py`
- `src/yuantus/meta_engine/tests/test_numbering_service.py`

已在 `main` 的相关文档：

- `docs/DEV_AND_VERIFICATION_NUMBERING_FLOOR_DB_PUSHDOWN_20260421.md`

本 MD 记录的是 merge / rerun / post-merge 执行本身。

## 9. 未做事项

- 未扩展到更多 SQL 方言
- 未改编号规则 schema
- 未启动下一条更大任务线

这些都应作为新的 bounded increment 独立推进，不与本 merge 归档混在一起。

## 10. 下一步建议

当前更合理的下一步不是继续微调 numbering，而是回到更高 ROI 的新增量：

1. 如果继续小改，做下一条明确的 hardening / dedup bounded increment
2. 如果切回产品线，给 `Suspended` 生命周期态单独写任务书，再开实现

## 11. 执行者

本轮由 Codex 执行：

- CI 失败归因
- failed-job rerun
- merge 执行
- local `main` sync
- focused regression
- merge 执行记录 MD 写盘
