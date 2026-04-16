# P2-2b Approval Escalation Review

Date: 2026-04-15

## Scope

Review Claude's `P2-2b` overdue approval escalation delivery from the actual code in the current working tree.

Reviewed files:

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_escalation.py`

## Verification

Focused verification:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "escalat or auto_assign or entity_type or request_create_and_list or export or approval_routing"
```

Result:

- `45 passed`
- `21 deselected`
- `1 warning`

Focused escalation suite:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py
```

Result:

- `10 passed`

## Findings

### 1. High: escalation skips generic bridge repair when an escalated ECOApproval already exists

Escalation currently short-circuits on any existing admin `ECOApproval`:

- `src/yuantus/meta_engine/services/eco_service.py:1882-1890`

But the generic `ApprovalRequest` bridge logic only runs inside the branch that creates a new `ECOApproval`:

- `src/yuantus/meta_engine/services/eco_service.py:1903-1934`

So if an admin already has an `ECOApproval` for the overdue `eco + stage`, but the generic bridge is missing or stale, repeated escalation will silently skip the admin and never repair the bridge.

That violates the requirement that ECO-local escalation and generic approvals remain synchronized.

### 2. High: non-approval stages with stale `approval_deadline` can still be escalated

`list_overdue_approvals()` currently includes any ECO with overdue `approval_deadline`, regardless of whether the current stage actually requires approval:

- `src/yuantus/meta_engine/services/eco_service.py:1336-1365`

`escalate_overdue_approvals()` then trusts that overdue list and does not re-check:

- `src/yuantus/meta_engine/services/eco_service.py:1868-1877`

So if a stage with `approval_type="none"` still has a stale deadline, escalation can create admin `ECOApproval` rows for a stage that should not be escalated at all.

## Verdict

This delivery is **not ready to sign off as-is**.

The minimum fixes are:

1. if an escalated `ECOApproval` already exists, still verify / repair the generic `ApprovalRequest` bridge instead of skipping the admin entirely
2. exclude non-approval stages from the overdue escalation path, either in `list_overdue_approvals()` or in `escalate_overdue_approvals()`
