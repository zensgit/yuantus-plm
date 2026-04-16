# P2-2a Approval Auto-Assign R4 Review

Date: 2026-04-15

## Scope

Review Claude's `P2-2a R4` delivery from the actual code in the current working tree.

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

- `22 passed`

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

No new blocking defects were identified in the reviewed `R4` slice.

The previously reported blockers are now addressed in the code that was reviewed:

- route now requires authenticated actor via `get_current_user_id`
- runtime permission check now uses `RBACUser.has_permission(...)`
- stage-aware bridge reuse distinguishes `draft/pending` from terminal states
- bridge failures are no longer silently swallowed in the endpoint path
- auto-progress path no longer suppresses auto-assign failures for approval-requiring next stages
- notification recipients now target concrete newly assigned user ids

## Residual Risks

### 1. No HTTP-level auth test yet

The new focused tests verify the route dependency by source inspection and service behavior by unit tests, but they do not exercise an end-to-end HTTP `401/403` path against a live test app.

This is a testing gap, not a reviewed runtime defect.

### 2. Zero-candidate stages still succeed

If a next stage requires approval but candidate resolution returns zero users, `auto_assign_stage_approvers(...)` still succeeds with an empty assignment set.

That may be acceptable if the domain intentionally allows unassigned / open approval stages, but if the intent is “approval-required stages must always have assigned approvers”, this should be tightened in a later slice.

## Verdict

Within the reviewed scope, this `R4` delivery is acceptable to sign off.
