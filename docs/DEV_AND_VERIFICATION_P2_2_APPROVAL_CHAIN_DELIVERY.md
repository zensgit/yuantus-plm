# P2-2: ECO Approval Chain — Unified Delivery

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-15
**Status:** ✅ 241 passed, 0 failed (38 focused approval tests)

---

## What This Delivery Contains

| Capability | Endpoint | Status |
|---|---|---|
| Approval routing read surface | `GET /eco/{eco_id}/approval-routing` | Mainline (pre-existing) |
| Auto-assign stage approvers | `POST /eco/{eco_id}/auto-assign-approvers` | P2-2a R5 |
| Overdue escalation to admin | `POST /eco/approvals/escalate-overdue` | P2-2b R2 |
| Generic ApprovalRequest bridge | Via auto-assign + escalation | P2-2a/b |

---

## Architecture

```
ECO enters stage (approval_type != "none")
  │
  ├─ auto_assign_stage_approvers(eco_id, user_id)
  │    ├─ RBAC permission: eco.auto_assign
  │    ├─ Resolve candidates: active users × active roles × stage.approval_roles
  │    ├─ Create ECOApproval(status=pending) per candidate
  │    ├─ Bridge: ApprovalRequest(entity_type="eco", properties.stage_id=...)
  │    │    ├─ Dedup: (eco, stage, user, state IN draft/pending) → reuse
  │    │    ├─ Draft → transition to pending
  │    │    ├─ Approved/rejected/cancelled → new pending
  │    │    └─ Failure → raise (no silent swallow)
  │    └─ Notify: only newly assigned user IDs
  │
  ├─ Users approve/reject via existing endpoints
  │
  └─ If overdue (approval_deadline passed):
       escalate_overdue_approvals(user_id)
         ├─ RBAC permission: eco.escalate_overdue
         ├─ Filter: only overdue + pending + stage.approval_type != "none"
         ├─ Target: active superusers
         ├─ Create ECOApproval(required_role="admin") + bridge
         │    └─ Bridge ALWAYS runs (even if ECOApproval already existed → repair)
         ├─ Idempotent: existing admin ECOApproval → skip create, still bridge
         └─ Notify: only newly escalated user IDs
```

---

## Auth & Permission Model

| Check | Mechanism | Result |
|---|---|---|
| No token | `get_current_user_id` dependency | HTTP 401 |
| Token but no permission | `_check_user_eco_permission` → `RBACUser.has_permission` | HTTP 403 |
| Superuser | `user.is_superuser` bypass | Allow |
| Normal user + permission | `has_permission("eco.auto_assign")` or `has_permission("eco.escalate_overdue")` | Allow |

Not using the broken `MetaPermissionService()` (instantiated without session). Direct `RBACUser.has_permission()` via DB lookup.

---

## Generic ApprovalRequest Bridge Contract

| Field | Value |
|---|---|
| `entity_type` | `"eco"` (lowercase) |
| `entity_id` | ECO ID |
| `assigned_to_id` | Target user ID |
| `properties.stage_id` | Stage ID (for stage-aware dedup) |
| `properties.escalated` | `True` (escalation only) |
| `priority` | `"normal"` (auto-assign) / `"urgent"` (escalation) |

Dedup key: `(entity_type, entity_id, assigned_to_id, properties.stage_id, state IN draft/pending)`

Bridge is queryable from existing generic approvals surface:
```
GET /approvals/requests?entity_type=eco&entity_id=eco-1
```

---

## Error Semantics

| Condition | Response |
|---|---|
| ECO not found | `ValueError` → 400 |
| No current stage | `ValueError` → 400 |
| Stage approval_type=none | `ValueError` → 400 |
| No matching candidates | `ValueError` → 400 |
| No active admin for escalation | `ValueError` → 400 |
| Bridge create/transition fails | Exception propagates → 500 + rollback |
| Permission denied | `PermissionError` → 403 |

No silent `except Exception: pass` anywhere.

---

## Files Changed

| File | P2-2a | P2-2b |
|---|---|---|
| `services/eco_service.py` | `_check_user_eco_permission`, `_resolve_candidate_users`, `auto_assign_stage_approvers`, `_user_has_stage_role` (inactive role fix), `approve()` wire-up | `escalate_overdue_approvals` (full rewrite) |
| `web/eco_router.py` | `POST /{eco_id}/auto-assign-approvers` | `POST /approvals/escalate-overdue` |
| `tests/test_eco_approval_auto_assign.py` | 26 tests | — |
| `tests/test_eco_approval_escalation.py` | — | 12 tests |

---

## Test Coverage

### P2-2a (26 tests)

| Class | Count | Covers |
|---|---|---|
| TestAuthHTTP | 6 | 401/403/superuser/permission/source-check |
| TestAutoAssignErrors | 3 | eco-not-found/stage-missing/none-type |
| TestBridgeStateAwareDedup | 4 | pending-reuse/completed-new/lowercase/properties |
| TestBridgeFailureRaises | 1 | bridge fail → raise |
| TestNotifications | 2 | user-IDs-only/idempotent-no-notify |
| TestInactiveFiltering | 2 | role/user |
| TestApproveAutoProgressFailure | 2 | permission-propagates/none-skips |
| TestDraftBridgeLifecycle | 2 | draft→pending/source-check |
| TestHTTPAuthIntegration | 3 | HTTP 401/403/200 via TestClient |
| TestEmptyCandidateError | 1 | no candidates → raise |

### P2-2b (12 tests)

| Class | Count | Covers |
|---|---|---|
| TestHTTPAuth | 3 | 401/403/200 |
| TestEscalationLogic | 4 | overdue-success/not-overdue/idempotent+bridge-repair/permission |
| TestEscalationBridge | 2 | lowercase-eco/failure-raises |
| TestEscalationNotifications | 1 | user-IDs-only |
| TestExistingApprovalBridgeRepair | 1 | existing ECOApproval → still bridge |
| TestNonApprovalStageExcluded | 1 | approval_type=none → skip |

---

## Verification Commands

```bash
# P2-2a + P2-2b combined
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  -v
# Expected: 38 passed

# Codex verification set
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "escalat or auto_assign or entity_type or request_create_and_list or export or approval_routing"

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

## What's Next

| Priority | Item | Scope |
|---|---|---|
| **P2-3** | ECO Stage SLA Dashboard (read surface) | `GET /eco/approvals/dashboard/summary` + `GET .../items` |
| P2-4 | Approval template / rule system | Deferred until P2-3 运营反馈 |
| — | BOM Diff UI / CAD Viewer UI | UI layer, lower priority |
| — | ECM Sunset | Zero-traffic 后清理 |
