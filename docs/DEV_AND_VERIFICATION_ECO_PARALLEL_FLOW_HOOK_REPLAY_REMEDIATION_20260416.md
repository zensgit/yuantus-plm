# ECO Parallel Flow Hook Replay Remediation

日期：2026-04-16

## 背景

`PR #220` clean replay 后，ECO 并行流与 apply diagnostics 相关 focused suites 出现 20 个已知失败：

- `test_eco_parallel_flow_hooks.py`: 15 failures
- `test_eco_apply_diagnostics.py`: 5 failures

问题集中在：

- `move_to_stage` / `action_apply` custom action hook 丢失 `context`
- `action_suspend` / `action_unsuspend` / `unsuspend-diagnostics` 运行时与路由缺失
- `compute_bom_changes()` / `POST /compute-changes` 丢失 `compare_mode`
- `action_apply()` / `get_apply_diagnostics()` 丢失 version checkout / file lock 守卫
- suspended ECO 的若干旁路未继续阻断

## 实际改动

### 1. `src/yuantus/meta_engine/services/eco_service.py`

- 恢复 `_resolve_actor_roles(...)`
- 恢复 `_run_custom_actions(..., context=...)`，并补 runtime scope：
  - `source`
  - `eco_id`
  - `stage_id`
  - `eco_priority`
  - `eco_type`
  - `product_id`
  - `workflow_map_id`
- `move_to_stage(...)`
  - 增加 suspended guard
  - before/after hook 补 `context={"stage_id", "actor_roles"}`
- `action_new_revision(...)`
  - 增加 suspended guard
- 恢复：
  - `action_suspend(...)`
  - `action_unsuspend(...)`
  - `get_unsuspend_diagnostics(...)`
  - `can_unsuspend(...)`
- `compute_bom_changes(...)`
  - 恢复 `compare_mode` 参数
  - 恢复 compare diff entry -> `ECOBOMChange` 投影路径
- `get_apply_diagnostics(...)`
  - 恢复 `eco.version_locks_clear`
  - 恢复 current/target version checkout 和 file-lock 诊断
- `action_apply(...)`
  - before/after hook 补 `actor_roles`
  - apply 前拒绝 foreign version checkout / file locks
  - `sync_version_files_to_item(...)` 显式传 `user_id`
- `ECOApprovalService.approve()/reject()`
  - suspended ECO 先行拒绝

### 2. `src/yuantus/meta_engine/web/eco_router.py`

- 恢复：
  - `GET /api/v1/eco/{eco_id}/unsuspend-diagnostics`
  - `POST /api/v1/eco/{eco_id}/suspend`
  - `POST /api/v1/eco/{eco_id}/unsuspend`
- 补 `_ensure_can_unsuspend_eco(...)`
- `POST /api/v1/eco/{eco_id}/compute-changes`
  - 恢复 `compare_mode` query param
  - 透传给 `service.compute_bom_changes(..., compare_mode=...)`

## 验证

### 1. 直接回归失败切片

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py
```

结果：

- `27 passed, 1 warning`

### 2. 相关审批链回归

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py
```

结果：

- `86 passed, 1 warning`

## 结论

- 原 20 个已知失败已全部修复
- `P2` approval chain focused slice 未出现回归
- 本次修复范围只涉及 ECO service/router runtime contract，不触碰 CAD / version / docs checklist 现有脏改动
