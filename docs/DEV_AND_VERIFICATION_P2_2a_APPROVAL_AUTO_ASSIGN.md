# P2-2a R5: ECO Approval Auto-Assignment — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-15
**Status:** ✅ 241 passed, 0 failed (26 focused tests)

---

## R4 → R5 修复项

### Fix R5-1: HTTP-level 401/403 集成测试

**问题**: 之前只有 source-inspection + service-level PermissionError 测试，没有真正的 HTTP 级验证。

**修复**: 新增 `TestHTTPAuthIntegration` — 用 `TestClient` + dependency override 验证：

```python
# 401: override get_current_user_id to raise 401
def override_no_user():
    raise HTTPException(status_code=401, detail="Unauthorized")

# 403: mock service to raise PermissionError
MockSvc.return_value.auto_assign_stage_approvers.side_effect = PermissionError(...)

# 200: mock service to return normal result
```

**Tests:**
- `test_http_401_when_no_user` — 无 token → 401
- `test_http_403_when_no_permission` — service raise PermissionError → 403
- `test_http_200_when_authorized` — 正常返回 → 200 + payload

### Fix R5-2: 空候选人 = 配置错误

**问题**: `approval_type=mandatory` 但 0 个候选人时，成功返回空 `{"assigned": []}`。

**修复**: 候选人为空时 raise ValueError。

```python
candidates = self._resolve_candidate_users(stage)
if not candidates:
    raise ValueError(
        f"Stage '{stage.name}' requires approval (roles={stage.approval_roles}) "
        f"but no active users with matching active roles were found"
    )
```

**Test:** `test_no_candidates_raises_value_error`

---

## 改动文件

| File | Change |
|---|---|
| `services/eco_service.py` | `auto_assign_stage_approvers`: 空候选人 raise ValueError |
| `tests/test_eco_approval_auto_assign.py` | +4 tests (HTTP 401/403/200, empty candidate); fix 2 existing auth test mocks |

未碰: `web/eco_router.py`, `checkin_service.py`, `job_worker.py`, `version/`, `file_router.py`, `cli.py`

---

## 完整 Focused Test 列表 (26)

```
TestAuthHTTP (6)
  test_router_uses_get_current_user_id_not_optional           PASSED
  test_user_not_found_raises_permission_error                  PASSED
  test_user_without_permission_raises                          PASSED
  test_superuser_bypasses_permission                           PASSED
  test_user_with_permission_allowed                            PASSED
  test_router_catches_permission_error_as_403                  PASSED

TestAutoAssignErrors (3)
  test_eco_not_found                                           PASSED
  test_stage_missing                                           PASSED
  test_stage_no_approval                                       PASSED

TestBridgeStateAwareDedup (4)
  test_pending_bridge_reused                                   PASSED
  test_completed_bridge_creates_new                            PASSED
  test_bridge_uses_lowercase_eco                               PASSED
  test_bridge_stores_stage_id_in_properties                    PASSED

TestBridgeFailureRaises (1)
  test_bridge_create_failure_raises                            PASSED

TestNotifications (2)
  test_notify_only_newly_assigned_user_ids                     PASSED
  test_idempotent_reentry_no_notification                      PASSED

TestInactiveFiltering (2)
  test_inactive_role_excluded                                  PASSED
  test_active_role_included                                    PASSED

TestApproveAutoProgressFailure (2)
  test_auto_assign_permission_error_propagates                 PASSED
  test_next_stage_no_approval_skips_auto_assign                PASSED

TestDraftBridgeLifecycle (2)
  test_existing_draft_transitioned_to_pending                  PASSED
  test_source_code_checks_draft_and_pending                    PASSED

TestHTTPAuthIntegration (3)  ← R5 新增
  test_http_401_when_no_user                                   PASSED
  test_http_403_when_no_permission                             PASSED
  test_http_200_when_authorized                                PASSED

TestEmptyCandidateError (1)  ← R5 新增
  test_no_candidates_raises_value_error                        PASSED

Total: 26 passed in 3.07s
```

---

## 验证命令

```bash
# P2-2a R5 focused
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py -v
# Expected: 26 passed

# Codex verification set
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "entity_type or request_create_and_list or export or approval_routing or auto_assign"

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

## 累计 R1→R5 验收对照

| 要求 | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| HTTP 401 (无 token) | ❌ | ✅ route | ✅ | ✅ | ✅ **HTTP 级** |
| HTTP 403 (无权限) | ❌ | ❌ | ✅ service | ✅ | ✅ **HTTP 级** |
| HTTP 200 (正常) | — | — | — | — | ✅ **HTTP 级** |
| ECO/stage/none 错误 | ❌ | ✅ | ✅ | ✅ | ✅ |
| 空候选人 | ❌ 空 200 | ❌ | ❌ | ❌ | ✅ **raise** |
| Inactive role/user | ❌ | ✅ | ✅ | ✅ | ✅ |
| Bridge lowercase "eco" | ❌ | ✅ | ✅ | ✅ | ✅ |
| Bridge stage dedup | ❌ | ❌ | ✅ | ✅ | ✅ |
| Bridge state dedup | — | — | ❌ | ✅ pending+draft | ✅ |
| Bridge 失败语义 | ❌ pass | ❌ | ✅ raise | ✅ | ✅ |
| 通知目标 | ❌ role | ❌ | ✅ user IDs | ✅ | ✅ |
| approve() auto-progress | — | — | ❌ catch | ✅ 条件 | ✅ |
| Draft bridge lifecycle | — | — | — | ✅ | ✅ |
