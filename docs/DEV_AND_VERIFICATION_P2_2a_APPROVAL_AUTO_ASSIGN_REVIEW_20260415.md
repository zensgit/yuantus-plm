# P2-2a Approval Auto-Assign Review

Date: 2026-04-15

## Scope

Review Claude's `P2-2a` approval auto-assign delivery from the actual code in the current working tree, not from the delivery summary alone.

Reviewed files:

- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/api/dependencies/auth.py`
- `src/yuantus/security/rbac/permissions.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py`

## Verification

Focused verification run:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "entity_type or request_create_and_list or export or approval_routing or auto_assign"
```

Result:

- `22 passed`
- `21 deselected`
- `1 warning`

## Findings

### 1. High: route auth / permission is still not real runtime protection

The new route is declared as:

- `POST /api/v1/eco/{eco_id}/auto-assign-approvers`

It depends on `get_current_user_id_optional`:

- `src/yuantus/meta_engine/web/eco_router.py:359-377`

But `get_current_user_id_optional()` returns `1` when there is no current user:

- `src/yuantus/api/dependencies/auth.py:314-319`

And the `PermissionManager` used by `ECOApprovalService` is still explicit allow-by-default:

- `src/yuantus/security/rbac/permissions.py:18-45`
- `src/yuantus/meta_engine/services/eco_service.py:36-47`

So the route does not currently satisfy the acceptance claim of “authenticated user with ECO update permission”. It only *appears* to do so at the service call site.

### 2. High: generic ApprovalRequest idempotency key is too coarse and collapses multi-stage approvals

The bridge reuses an existing generic request if it finds any record with:

- `entity_type="eco"`
- `entity_id=eco_id`
- `assigned_to_id=user_id`

See:

- `src/yuantus/meta_engine/services/eco_service.py:1739-1748`

This ignores the ECO stage. If the same approver is assigned again on a later ECO stage, the bridge will reuse the earlier `ApprovalRequest` instead of creating a new pending request for the new stage.

That means the generic approvals inbox can lose stage-level work items even though ECO-local `ECOApproval` rows are newly created.

### 3. Medium: bridge failures are silently swallowed, so the two approval domains can drift apart

Bridge creation is wrapped in:

- `except Exception: pass`

See:

- `src/yuantus/meta_engine/services/eco_service.py:1739-1760`

So the endpoint can return success with newly created `ECOApproval` rows while creating no corresponding generic `ApprovalRequest`. That violates the stated goal that auto-assigned approvals remain visible from the generic approvals read surface.

### 4. Medium: notification recipients are still role buckets, not the final assigned users

The implementation says “Notify only newly assigned users”, but the actual `recipients=` value is still built from stage role names via `_resolve_stage_recipients(stage)`:

- `src/yuantus/meta_engine/services/eco_service.py:79-85`
- `src/yuantus/meta_engine/services/eco_service.py:1762-1778`

So this does not actually prove that only the final assigned users are notified. It still fans out through the stage recipient resolver rather than the concrete `newly_assigned_user_ids`.

### 5. Medium: the new tests overstate route-auth and bridge-queryability coverage

Two acceptance claims are not really proven by the new focused tests:

- “router auth / permission test” only checks that `service.permission_service.check_permission(...)` was called, not that the HTTP route enforces authentication semantics
- “generic bridge queryable” uses a mocked session and asserts `len(results) >= 0`, which does not prove the newly created bridge record is discoverable through the real approvals read surface

See:

- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py:61-75`
- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py:247-256`

## Verdict

This delivery is **not ready to sign off as-is**.

The two blockers are:

1. runtime auth / permission is not actually enforced
2. the generic bridge idempotency key is not stage-aware

The bridge failure swallowing and notification fan-out issues should also be fixed before merge if the intent is to claim end-to-end approvals read-surface compatibility.

## Recommended Fix Order

1. Make the route require a real authenticated actor instead of relying on `get_current_user_id_optional() -> 1`.
2. Make the generic bridge stage-aware, so one approver can receive distinct generic requests across ECO stages.
3. Remove or narrow the blanket `except Exception: pass` around bridge creation.
4. Send notifications to the concrete assigned users rather than the stage role bucket.
