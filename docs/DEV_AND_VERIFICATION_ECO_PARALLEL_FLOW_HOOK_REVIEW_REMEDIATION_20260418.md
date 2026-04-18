# ECO Parallel Flow Hook Review Remediation

日期：2026-04-18
目标 PR：`#222 fix(eco): restore parallel flow hook and diagnostics contracts`

## 目标

收口 `#222` 上剩余的 review blocker，重点修正：

- `suspend` / `unsuspend` / `unsuspend-diagnostics` 的认证语义
- `PermissionError` 被错误映射为 `500` 的路由行为
- `eco_service.py` 中过宽的异常捕获

这轮修复完成后，`#222` 才适合作为下一轮 frozen remote observation 的目标变更。

## 实际改动

### 1. `src/yuantus/meta_engine/web/eco_router.py`

- `GET /api/v1/eco/{eco_id}/unsuspend-diagnostics`
  - 改为依赖 `get_current_user_optional`
  - `ECO` 存在但未登录时返回 `401`
  - 已登录但无权限时保持 `403`
  - `ECO` 不存在时仍允许返回结构化 diagnostics，并显式以匿名 `user_id=0` 调 service
- `POST /api/v1/eco/{eco_id}/suspend`
  - 改为依赖 `get_current_user_id`
  - 未登录直接 `401`
  - `PermissionError` 映射为 `403`
  - `PermissionError` 前补 `db.rollback()`
- `POST /api/v1/eco/{eco_id}/unsuspend`
  - 改为依赖 `get_current_user_id`
  - 未登录直接 `401`
  - `PermissionError` 映射为 `403`
  - `PermissionError` 前补 `db.rollback()`

### 2. `src/yuantus/meta_engine/services/eco_service.py`

- `_resolve_actor_roles(...)`
  - 去掉不必要的 `int()` 强转和 broad `except`
  - 直接按传入 `user_id` 查询 `RBACUser`
- `get_apply_diagnostics(...)`
  - `eco.target_version_exists`
  - `eco.version_locks_clear`
  - `current_version` lookup
  - 上述路径都只对 `VersionError` 做“版本缺失 -> 继续诊断”兜底
  - 其它异常继续透出，不再被 broad `except Exception` 吃掉

## 补充测试

### 1. `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`

- `unsuspend-diagnostics`
  - 匿名缺失 `ECO` 时使用 `user_id=0`
  - 已存在 `ECO` 且匿名访问时返回 `401`
  - 权限不足时返回 `403`
- `suspend`
  - 未登录返回 `401`
  - `PermissionError` 返回 `403`
- `unsuspend`
  - 未登录返回 `401`
  - `PermissionError` 返回 `403`

### 2. `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

- `_resolve_actor_roles(...)` 不再做多余类型强转
- `get_apply_diagnostics(...)` 对 `VersionError` 的兜底行为
- `get_apply_diagnostics(...)` 对非 `VersionError` 的异常透传

## 验证

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py
```

结果：

- `38 passed`
- 现有环境 warning：`urllib3` / `LibreSSL`

文档契约验证：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

## 结论

- `#222` 的 review blocker 已从“未认证落到默认用户 / 403 误打成 500 / broad exception”收敛为明确的可验证行为
- 这轮修复完成后，`#222` 更适合作为后续 frozen remote observation 的目标变更
- 远端冻结观察仍应在 `#222` 合并后执行，只读对照当前稳定基线
