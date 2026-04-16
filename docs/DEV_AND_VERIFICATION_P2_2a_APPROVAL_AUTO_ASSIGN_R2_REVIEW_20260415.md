# P2-2a Approval Auto-Assign R2 Review

Date: 2026-04-15

## Scope

Review Claude's `P2-2a R2` delivery from the current working tree implementation.

Reviewed files:

- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/api/dependencies/auth.py`
- `src/yuantus/security/rbac/permissions.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py`

## Verification

Focused verification:

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

Additional focused suite:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py
```

Result:

- `15 passed`

## Findings

### 1. High: authenticated route, but still no real authorization boundary

R2 correctly switched the route from `get_current_user_id_optional` to `get_current_user_id`:

- `src/yuantus/meta_engine/web/eco_router.py:359-377`

However the service still relies on the same allow-by-default `PermissionManager`:

- `src/yuantus/meta_engine/services/eco_service.py:1677`
- `src/yuantus/security/rbac/permissions.py:18-45`

So unauthenticated access is now blocked, but any authenticated actor still passes the mutation gate unless the global permission substrate changes. This means the “auth / permission” acceptance item is only partially satisfied.

### 2. Medium: stage-aware dedup reuses any matching bridge row regardless of request state

The new dedup query is now stage-aware:

- `src/yuantus/meta_engine/services/eco_service.py:1739-1748`

But it reuses the first matching `ApprovalRequest` without checking whether that request is still in a reusable state. If the existing bridge row for the same `eco + stage + user` is already `approved`, `rejected`, or `cancelled`, this code still reuses it and skips creating a fresh pending request.

That breaks the stated requirement that the generic approvals bridge state remain aligned with the ECO-local pending approval state.

### 3. Medium: notifications still fan out to stage recipient buckets, not the final assigned users

The implementation says “Notify only newly assigned users, not duplicates”, but the actual recipients are still resolved from the stage:

- `src/yuantus/meta_engine/services/eco_service.py:1762-1778`
- `src/yuantus/meta_engine/services/eco_service.py:79-85`

So the runtime notification behavior is still role-bucket based, not strictly the concrete `newly_assigned_user_ids`.

### 4. Medium: bridge failures are still silently swallowed

The bridge path still wraps the new stage-aware JSONB query and request creation in a blanket:

- `except Exception: pass`

See:

- `src/yuantus/meta_engine/services/eco_service.py:1739-1760`

That means the endpoint can succeed with newly created `ECOApproval` rows while creating no corresponding generic `ApprovalRequest`, leaving the two approval domains out of sync.

## Verdict

R2 fixes the two previously reported blockers only **partially**:

- route authentication: fixed
- stage-aware dedup key: improved

But this review still does **not** recommend direct sign-off yet.

The remaining merge blockers are:

1. no real authorization boundary beyond “authenticated user”
2. reused stage-aware bridge records do not validate / repair request state

The notification fan-out and blanket bridge failure swallowing should also be addressed before merge if this feature is meant to claim end-to-end approvals read-surface compatibility.
