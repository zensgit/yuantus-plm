## P2-3.1 PR-3 Approval Audit Review

Date: 2026-04-16

### Conclusion

Do not sign off PR-3 yet. One blocker remains in the `escalated_unresolved` query.

### Findings

1. High: `escalated_unresolved` is not bound to the ECO's current stage, so historical admin-pending approvals from prior stages can be reported as current unresolved anomalies.
   - Runtime code:
     - `src/yuantus/meta_engine/services/eco_service.py:1628-1637`
   - Current query:
     - joins `ECOApproval -> ECO`
     - joins `ECOApproval.stage_id -> ECOStage.id`
     - but does **not** require `ECOApproval.stage_id == ECO.stage_id`
   - Effect:
     - if an ECO moved to a new stage while an old admin escalation row remained pending, this audit report will still flag that old-stage row as "unresolved".
   - This is the same class of issue that previously affected dashboard items before the stage-binding fix.

2. Medium: focused tests do not cover the current-stage binding rule for `escalated_unresolved`.
   - File:
     - `src/yuantus/meta_engine/tests/test_eco_approval_audit.py`
   - Coverage currently proves:
     - route exists
     - shape is returned
     - the three anomaly buckets can be populated
   - It does not prove:
     - old-stage admin pending rows are excluded

### Verification Run

Focused:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py
```

Result: `8 passed, 1 warning`

Related slice:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "audit or dashboard or export or escalat or auto_assign or approval_routing or entity_type or request_create_and_list"
```

Result: `94 passed, 21 deselected, 1 warning`

### Minimal Fix

1. In the `escalated_unresolved` query, require current-stage binding:
   - add `ECOApproval.stage_id == ECO.stage_id`
2. Add one focused test:
   - old-stage admin pending approval exists
   - ECO has already moved to a different current stage
   - anomaly report must **not** include the old-stage row
