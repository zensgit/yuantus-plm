# P2-2a Approval Auto-Assign R3 Review

Date: 2026-04-15

## Scope

Review Claude's `P2-2a R3` delivery from the actual code in the current working tree.

Reviewed files:

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py`
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/security/rbac/models.py`

## Verification

Focused suite:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py
```

Result:

- `18 passed`

Bridge/read-surface subset:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "entity_type or request_create_and_list or export or approval_routing or auto_assign"
```

Result:

- `27 passed`
- `21 deselected`
- `1 warning`

## Findings

### 1. High: auto-progress path still swallows all auto-assign failures

`approve()` now wires the new auto-assign path on stage auto-progress, but it still wraps the call in:

- `except (ValueError, Exception): pass`

See:

- `src/yuantus/meta_engine/services/eco_service.py:1439-1446`

This means the newly fixed runtime guarantees are bypassed on the most important automatic path:

- missing `eco.auto_assign` permission
- generic bridge failure
- unexpected stage-aware JSON query failure

All of those are silently ignored and the ECO still advances to the next stage.

So manual `POST /auto-assign-approvers` is now stricter, but automatic stage progression can still leave the next stage without assigned generic approvals.

### 2. Medium: stage-aware bridge reuse still ignores existing `draft` requests

R3 correctly narrowed reuse to:

- same `eco`
- same `stage`
- same `user`
- `state == pending`

See:

- `src/yuantus/meta_engine/services/eco_service.py:1739-1748`

But the implementation still does not repair an existing `draft` request into `pending`. It creates a new request instead.

That is narrower and safer than R2, but it still does not fully satisfy the desired bridge lifecycle rule:

- `pending` -> reuse
- `draft` -> transition to `pending`
- `approved/rejected/cancelled` -> create new

## Verdict

R3 is materially better than R2:

- route now requires authenticated actor
- permission check now uses `RBACUser.has_permission(...)`
- bridge dedup is stage-aware and state-aware for `pending`
- bridge failure is no longer silently swallowed in the endpoint path
- notifications now target concrete assigned user ids

However, I still do **not** recommend direct sign-off yet because the auto-progress path still swallows all auto-assign failures.

## Minimal R4 Fix

1. In `approve()` auto-progress flow, stop catching blanket `Exception`.
2. If the next stage requires approval, treat auto-assign failure as a real operation failure, not a silent no-op.
3. Optionally tighten bridge handling for existing `draft` requests by transitioning them to `pending` instead of creating a duplicate.
