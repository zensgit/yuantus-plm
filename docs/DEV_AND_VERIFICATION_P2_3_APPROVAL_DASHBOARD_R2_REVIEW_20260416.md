## P2-3 Approval Dashboard R2 Review

Date: 2026-04-16

### Conclusion

R2 addresses the two previously blocking issues. No new blockers found.

### Verified Fixes

1. Current-stage binding is now enforced in the shared base query.
   - `src/yuantus/meta_engine/services/eco_service.py:1371-1389`
   - `ECOApproval.stage_id == ECO.stage_id` is part of the join condition.

2. Summary and items now derive from the same filtered approval row set.
   - `src/yuantus/meta_engine/services/eco_service.py:1392-1443`
   - `src/yuantus/meta_engine/services/eco_service.py:1445-1494`
   - This fixes the earlier mismatch where headline counts were ECO-level while detail rows were approval-level.

### Residual Risks

1. Dashboard HTTP tests still patch the service layer, so route coverage is contract-level rather than end-to-end data-driven.
2. `by_role` remains stage-role based, not assignee-role based. This is acceptable if the intended dashboard dimension is "stage approval buckets", but it should be documented explicitly.

### Verification Run

Focused:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py
```

Result: `17 passed, 1 warning`

Related slice:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "dashboard or escalat or auto_assign or approval_routing or entity_type or request_create_and_list or export"
```

Result: `64 passed, 21 deselected, 1 warning`
