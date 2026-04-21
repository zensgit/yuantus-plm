# DEV_AND_VERIFICATION_LIFECYCLE_SUSPENDED_GUARD_TASK_REVIEW_20260421

## 1. 目标

审阅 `docs/DEVELOPMENT_CLAUDE_TASK_LIFECYCLE_SUSPENDED_GUARD_20260421.md`，判断它是否可以交给 Claude Code CLI 执行，并在任务书中补齐会影响实现正确性的缺口。

本轮只审任务书，不实现 `LifecycleState.is_suspended`、`SuspendedGuardService` 或写路径 guard。

## 2. 审阅结论

结论：**可以交给 Claude 执行，但必须带着本轮补丁后的任务书执行**。

原任务书的方向是对的：

- `Suspended` 状态已经存在，不应重建 lifecycle
- 本轮应只补 `is_suspended` 语义字段和 write-time guard
- `latest_released_guard.py` 是合适模板
- scoped config 复用 `meta_plugin_configs` 是正确路线

但原任务书漏了 3 个会导致实现返工的真实代码入口。本轮已直接 patch 到任务书。

## 3. 已补齐的问题

### 3.1 Router 映射不止 `web/router.py`

原任务书只要求在 `src/yuantus/meta_engine/web/router.py` 加 `SuspendedStateError -> 409`。

实际代码里 latest-released 409 映射分布在 3 个入口：

- `src/yuantus/meta_engine/web/router.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/meta_engine/web/effectivity_router.py`

如果只改 `web/router.py`，BOM `add_child`、BOM substitute、Effectivity create 抛出的 `SuspendedStateError` 可能变成 500/400，而不是稳定 409。

任务书已修正为：3 个 router 都必须补映射和 HTTP 测试。

### 3.2 Seeder 路径不止 `seeder/meta/lifecycles.py`

原任务书只要求更新：

- `src/yuantus/seeder/meta/lifecycles.py`

实际开发和 smoke 常用的 `seed-meta` 还在：

- `src/yuantus/cli.py::seed_meta`

该 CLI 内部也会创建 Part/Document lifecycle 的 `Suspended` state。如果只改 registry seeder，`seed-meta` 路径下的 Part `Suspended` 会漏标 `is_suspended=True`。

任务书已修正为：两个 seeder 路径都要覆盖；本 bounded increment 只要求 Part lifecycle，不扩 Document lifecycle 语义。

### 3.3 State resolution 不能只传 `item_type=None`

原任务书写的是通过 `get_lifecycle_state(session, item, item_type=None)` 获取 state。

实际 `get_lifecycle_state(...)` 的 fallback 依赖 `ItemType.lifecycle_map_id`：

- `item.current_state` 有值时可直接查 FK
- `item.current_state` 缺失时，必须传入 `item_type` 才能用 `item.state` + lifecycle map 回查

如果实现永远传 `item_type=None`，会漏掉只有 `state="Suspended"` 但 `current_state` 缺失的历史/测试数据。

任务书已修正为：Item target 必须加载 `Item` + `ItemType`，Version target 必须加载 parent `Item` + `ItemType`，Relationship effectivity target 必须先解引用 `related_id`。

## 4. 其他审阅调整

本轮还补了以下实现约束：

- Alembic migration 要遵循 repo 现有 idempotent inspector pattern
- SQLite 用 `batch_alter_table`
- `is_suspended` 列要求 `nullable=False` + `server_default=sa.false()`
- `SubstituteService.ensure_substitute_item_type()` 的 bootstrap commit 不计入半成品 substitute row，事务验收关注业务 relationship 不残留
- 遗留 merge record 收口只收当前实际未提交的 `PR309` merge MD，不重复添加已在 main 的 PR300/PR294 记录

## 5. 验证

本轮执行的是文档级审阅和契约验证。

检查过的真实代码入口：

- `src/yuantus/meta_engine/services/latest_released_guard.py`
- `src/yuantus/meta_engine/web/router.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/meta_engine/web/effectivity_router.py`
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/services/substitute_service.py`
- `src/yuantus/meta_engine/services/effectivity_service.py`
- `src/yuantus/meta_engine/operations/add_op.py`
- `src/yuantus/seeder/meta/lifecycles.py`
- `src/yuantus/cli.py`
- `src/yuantus/meta_engine/lifecycle/guard.py`

契约测试：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：`3 passed in 0.02s`

## 6. 给 Claude 的执行建议

可以让 Claude 执行，但必须明确：

- 使用补丁后的 `docs/DEVELOPMENT_CLAUDE_TASK_LIFECYCLE_SUSPENDED_GUARD_20260421.md`
- 不要按旧版任务书只改一个 router
- 不要只改 registry seeder
- 不要用 `state.name == "Suspended"` 字符串硬匹配替代 `is_suspended`
- 不要启动 UI、scheduler、previous_state 或跨模块扩散

## 7. 边界

本轮未做：

- runtime schema / migration 实现
- `SuspendedGuardService` 实现
- 写路径代码挂接
- Claude CLI 执行

这些留给下一条 feature PR。
