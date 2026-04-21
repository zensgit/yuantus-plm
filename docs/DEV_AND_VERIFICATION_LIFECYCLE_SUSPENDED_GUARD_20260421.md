# DEV_AND_VERIFICATION_LIFECYCLE_SUSPENDED_GUARD_20260421

## 1. 目标

本轮实现 Lifecycle Suspended Guard 的 backend bounded increment：

- 在 `LifecycleState` 增加 `is_suspended` 语义字段
- seed `Part` lifecycle 的 `Suspended` state 为 `is_suspended=True`
- 新增 `SuspendedGuardService`
- 在 BOM / Substitute / Effectivity / AML nested relationship 四条写路径加 write-time guard
- 在对应 HTTP router 中把 `SuspendedStateError` 稳定映射为 `409`

不做：

- UI
- scheduler
- previous_state / 自动 resume
- 跨采购、销售、工单、质量等模块扩散
- 新管理端点

## 2. 设计选择

### 2.1 为什么字段落在 `LifecycleState`

Suspended 是 lifecycle state 的语义，不是单个 `Item` 的动态属性。

把 `is_suspended` 放在 `LifecycleState` 上可以让系统避免：

- `state.name == "Suspended"` 字符串硬匹配
- 多语言 label 变化导致 guard 失效
- 不同 lifecycle state 名称差异导致误判

### 2.2 为什么复用 scoped config

`SuspendedGuardService` 复用 `LatestReleasedGuardService` 的灰度模式：

- settings fallback：`SUSPENDED_GUARD_DISABLED`
- scoped config：`meta_plugin_configs`
- plugin id：`suspended-guard`
- disabled key：`disabled`

这样不会为 Suspended guard 发明新配置机制。

### 2.3 判定口径

Item target：

- 加载 `Item`
- 加载对应 `ItemType`
- 通过 `get_lifecycle_state(session, item, item_type)` 解析 state
- 读取 `LifecycleState.is_suspended`

Effectivity relationship target：

- 如果 target 是 relationship item 且有 `related_id`
- 先解引用 related item
- 再按 Item target 规则检查

Version target：

- 加载 `ItemVersion`
- 加载 parent `Item` + `ItemType`
- 优先检查 parent item lifecycle state
- 再用 `version.state` + parent item lifecycle map fallback 解析 `LifecycleState`

## 3. 改动范围

### 3.1 Schema / Migration

- `src/yuantus/meta_engine/lifecycle/models.py`
- `migrations/versions/f4a5b6c7d8e9_add_lifecycle_state_is_suspended.py`

Migration 特点：

- down revision：`e3f4a5b6c7d8`
- idempotent inspector pattern
- SQLite 走 `batch_alter_table`
- `is_suspended` 为 `nullable=False` + `server_default=sa.false()`

### 3.2 Seeder

- `src/yuantus/seeder/meta/lifecycles.py`
- `src/yuantus/cli.py::seed_meta`

两条 seed 路径都覆盖 Part lifecycle 的 `Suspended` state。

### 3.3 Guard Service

- `src/yuantus/meta_engine/services/suspended_guard.py`

新增：

- `SUSPENDED_GUARD_PLUGIN_ID = "suspended-guard"`
- `SUSPENDED_GUARD_DISABLED_KEY = "disabled"`
- `SuspendedStateError`
- `SuspendedGuardService`
- `assert_not_suspended(...)`

### 3.4 写路径接入

- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/services/substitute_service.py`
- `src/yuantus/meta_engine/services/effectivity_service.py`
- `src/yuantus/meta_engine/operations/add_op.py`

顺序保持：

1. `assert_latest_released(...)`
2. `assert_not_suspended(...)`

这样 stale/latest 分类优先，Suspended 分类随后生效。

### 3.5 HTTP 映射

- `src/yuantus/meta_engine/web/router.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/meta_engine/web/effectivity_router.py`

全部把 `SuspendedStateError` 映射为 `409`，detail 使用 `to_detail()`。

## 4. 测试覆盖

新增 / 扩展：

- `src/yuantus/meta_engine/tests/test_suspended_guard.py`
- `src/yuantus/meta_engine/tests/test_suspended_write_paths.py`
- `src/yuantus/meta_engine/tests/test_suspended_guard_seed_migration_contracts.py`
- `src/yuantus/meta_engine/tests/test_latest_released_guard_router.py`
- `src/yuantus/meta_engine/tests/test_latest_released_write_paths.py`
- `src/yuantus/meta_engine/operations/tests/test_add_op.py`

覆盖点：

- 默认启用
- settings fallback 禁用
- tenant-org scoped config 禁用
- tenant-default scoped config 禁用
- item current_state 判定
- item.state + item_type lifecycle fallback 判定
- relationship related item 判定
- version.state fallback 判定
- BOM / Substitute / Effectivity / AML nested relationship 写路径挂接
- `SuspendedStateError -> 409`
- migration/seeder contract
- 失败时业务 relationship / effectivity 不残留

## 5. 验证

### 5.1 Suspended focused tests

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_suspended_guard.py \
  src/yuantus/meta_engine/tests/test_suspended_write_paths.py \
  src/yuantus/meta_engine/tests/test_suspended_guard_seed_migration_contracts.py
```

结果：`19 passed in 0.42s`

### 5.2 Adjacent latest-released / router / add-op regression

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/operations/tests/test_add_op.py
```

结果：`18 passed in 0.77s`

### 5.3 Combined focused regression

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_suspended_guard.py \
  src/yuantus/meta_engine/tests/test_suspended_write_paths.py \
  src/yuantus/meta_engine/tests/test_suspended_guard_seed_migration_contracts.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py
```

结果：`48 passed in 0.78s`

### 5.4 Alembic SQLite upgrade

```bash
YUANTUS_DATABASE_URL="sqlite:////tmp/yuantus-suspended-XXXXXX.db" \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m alembic upgrade head
```

结果：`MIGRATION_OK`

### 5.5 Doc-index contracts

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：`3 passed in 0.02s`

### 5.6 CI contracts wiring remediation

PR #310 首轮 GitHub `contracts` job 失败：

```text
Contract checks missing from .github/workflows/ci.yml contracts step:
- src/yuantus/meta_engine/tests/test_suspended_guard_seed_migration_contracts.py
```

修复：

- `.github/workflows/ci.yml` contracts step 显式登记 `test_suspended_guard_seed_migration_contracts.py`

本地验证：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_suspended_guard_seed_migration_contracts.py
```

结果：`4 passed in 0.01s`

### 5.7 Full pytest attempt

第一次直接执行：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q
```

结果：collection 阶段失败，API 测试未解析到 `yuantus` 包，报 `ModuleNotFoundError: No module named 'yuantus'`。

第二次补 `PYTHONPATH=src`：

```bash
PYTHONPATH=src /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q
```

结果：`177 failed, 130 passed`，失败集中在 router/API 测试期望 `200/403/404` 但实际收到 `401 Unauthorized`。这些失败集中在 baseline、ECO diagnostics、parallel tasks、release readiness/orchestration 等认证测试面，不经过本轮 Suspended guard 代码路径。

结论：本轮不把当前本机 full pytest 作为 merge gate；采用 focused regression、migration upgrade、doc-index contracts 作为有效验证。

## 6. 已知边界

- 只处理 Part lifecycle 的 Suspended state
- 不扩展 Document lifecycle Suspended 语义
- 不提供管理端点，灰度配置继续通过现有 plugin config 机制写入
- 不改变 latest-released guard 的错误分类优先级
- Substitute service 内部 `ensure_substitute_item_type()` 的 bootstrap commit 保持现状；本轮只保证业务 substitute relationship 在 guard 失败时不创建

## 7. 结论

本轮实现了 Odoo `plm_suspended` 对标能力的 backend 最小闭环：

- lifecycle state 具备程序化 suspended 语义
- 下游消费写路径统一阻断 Suspended target
- 租户/org scoped config 可灰度回滚
- HTTP 层稳定返回 `409 SUSPENDED_STATE`

Line A / Line B 既有能力未改动，latest-released guard 行为保持原顺序。
