# P2-2b R2: Overdue Approval Escalation — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-15
**Status:** ✅ 241 passed, 0 failed (12 focused tests)

---

## R1 → R2 修复

### Fix 1 (High): 已有 ECOApproval 时仍修 bridge

**问题**: admin 已有 ECOApproval → `continue` 跳过 → bridge 不修 → 两域漂移。

**修复**: ECOApproval 存在与否不影响 bridge 逻辑。拆分为：
- ECOApproval 存在 → 不重复创建，记录 `appr_id`
- ECOApproval 不存在 → 创建新的
- **Bridge 始终执行** — 查 existing AR → 有 draft 则 transition pending → 没有则 create

```python
if existing_appr:
    appr_id = existing_appr.id
else:
    new_appr = ECOApproval(...)
    appr_id = new_appr.id

# Bridge ALWAYS runs — even when ECOApproval already existed
existing_ar = session.query(ApprovalRequest).filter(...).first()
if existing_ar:
    if existing_ar.state == "draft":
        ar_service.transition_request(existing_ar.id, target_state="pending")
else:
    ar = ar_service.create_request(...)
```

**Test**: `test_existing_eco_approval_still_creates_bridge` — 验证 ECOApproval 存在时 `create_request` 仍被调用

### Fix 2 (High): non-approval stage 排除

**问题**: `list_overdue_approvals()` 只按 deadline+state 取 ECO，不排除 `approval_type="none"` 的 stage → stale deadline 会导致给不需审批的 stage 创建 admin ECOApproval。

**修复**: escalation 循环体开头加：

```python
if stage.approval_type == "none":
    continue
```

**Test**: `test_approval_type_none_skipped` — approval_type="none" → `escalated: 0`, 无通知

---

## 改动文件

| File | Change |
|---|---|
| `services/eco_service.py` | `escalate_overdue_approvals`: bridge 逻辑移到 ECOApproval check 外面 + `approval_type=="none"` guard |
| `tests/test_eco_approval_escalation.py` | +2 new tests, 1 updated (idempotent now verifies bridge repair); all stage mocks add `approval_type="mandatory"` |

未碰: `eco_router.py`, P2-2a 文件, CAD/version/lock/cli

---

## Focused Tests (12)

```
TestHTTPAuth (3)
  test_401_no_auth                                      PASSED
  test_403_no_permission                                PASSED
  test_200_authorized                                   PASSED

TestEscalationLogic (4)
  test_overdue_pending_escalated                        PASSED
  test_not_overdue_noop                                 PASSED
  test_idempotent_repeated_call                         PASSED  ← updated: verifies bridge repair
  test_permission_denied                                PASSED

TestEscalationBridge (2)
  test_bridge_created_with_lowercase_eco                PASSED
  test_bridge_failure_raises                            PASSED

TestEscalationNotifications (1)
  test_notify_only_newly_escalated_users                PASSED

TestExistingApprovalBridgeRepair (1)  ← R2 new
  test_existing_eco_approval_still_creates_bridge       PASSED

TestNonApprovalStageExcluded (1)  ← R2 new
  test_approval_type_none_skipped                       PASSED
```

---

## 验证命令

```bash
# P2-2b focused
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_escalation.py -v
# Expected: 12 passed

# P2-2a + P2-2b combined
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  -v
# Expected: 38 passed

# Codex verification set
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "escalat or auto_assign or entity_type or request_create_and_list or export or approval_routing"

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

## 验收对照

| 要求 | R1 | R2 |
|---|---|---|
| HTTP 401/403/200 | ✅ | ✅ |
| Only pending overdue | ✅ | ✅ |
| Non-approval stage excluded | ❌ | ✅ |
| Deterministic admin target | ✅ | ✅ |
| ECOApproval + bridge sync | ❌ existing skip | ✅ always bridge |
| entity_type="eco" | ✅ | ✅ |
| Idempotent | ✅ ECO level | ✅ ECO + bridge |
| Notify only new escalated | ✅ | ✅ |
| Bridge failure raises | ✅ | ✅ |
