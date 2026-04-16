# P2-2b Approval Escalation R2 Review

Date: 2026-04-15

## Scope

Review Claude's `P2-2b R2` delivery from the actual code in the current working tree.

Reviewed files:

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_approval_escalation.py`

## Verification

Focused verification:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py
```

Result:

- `12 passed`

Bridge/read-surface subset:

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

## Findings

No new blocking defects were identified in the reviewed `R2` slice.

The two previously reported blockers are addressed in the reviewed code:

- if an escalated `ECOApproval` already exists, the generic `ApprovalRequest` bridge is still checked / repaired instead of being skipped
- stages with `approval_type="none"` are explicitly excluded from the escalation write path even if stale `approval_deadline` data exists

## Residual Risks

### 1. Escalation target policy is still minimal

The current implementation escalates to active superusers. This is acceptable for the current small-scope slice, but it is still a minimal policy rather than a configurable escalation chain.

### 2. HTTP permission coverage is still route-level, not data-backed RBAC integration

The HTTP `401/403/200` tests validate router behavior through dependency overrides and patched service outcomes. They are good focused contract tests, but they do not yet prove end-to-end permission data wiring against a real RBAC fixture.

## Verdict

Within the reviewed scope, this `P2-2b R2` delivery is acceptable to sign off.
