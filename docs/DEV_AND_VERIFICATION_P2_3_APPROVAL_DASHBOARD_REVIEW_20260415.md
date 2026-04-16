## P2-3 Approval Dashboard Review

Date: 2026-04-15

### Conclusion

Do not sign off this P2-3 dashboard slice yet.

### Findings

1. High: `items` joins `ECOApproval` only by `eco_id`, so stale pending approvals from previous stages can appear under the current stage dashboard item list.
   - Runtime code:
     - `src/yuantus/meta_engine/services/eco_service.py:1481-1489`
     - `src/yuantus/meta_engine/services/eco_service.py:1514-1539`
   - Why this is real:
     - `approve()` advances `eco.stage_id` once `min_approvals` is reached.
     - It does not clear or close other users' pending approvals on the previous stage.
     - Relevant path:
       - `src/yuantus/meta_engine/services/eco_service.py:1573-1595`
       - `src/yuantus/meta_engine/services/eco_service.py:1597-1618`
   - Effect:
     - Historical `ECOApproval(stage_id=old_stage, status=pending)` rows can still join to the ECO after it has moved to `new_stage`.
     - The dashboard then labels them with `stage_name` from `ECO.stage_id`, not the approval row's own stage.

2. High: `summary` mixes ECO-level counts with approval-level aggregates, so the headline numbers do not reconcile with `items`, `by_assignee`, or escalated counts.
   - Runtime code:
     - `src/yuantus/meta_engine/services/eco_service.py:1375-1412`
     - `src/yuantus/meta_engine/services/eco_service.py:1414-1466`
   - Why this is real:
     - `pending_count` / `overdue_count` are counted from `ECO + current stage` rows.
     - `escalated_count` and `by_assignee` are counted from pending `ECOApproval` rows.
   - Effect:
     - One ECO with two pending approvers can produce:
       - `pending_count = 1`
       - `by_assignee total = 2`
       - `items length = 2`
     - This makes the dashboard summary internally inconsistent.

3. Medium: focused tests are too mock-heavy to prove the real query semantics.
   - Test file:
     - `src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py`
   - Examples:
     - Filter coverage for `overdue` / `escalated` relies on source inspection instead of data assertions.
     - HTTP tests patch the service and only prove route registration + 200 mapping.
     - There is no fixture covering:
       - prior-stage pending approvals
       - `summary` vs `items` reconciliation

### Verification Run

Focused:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py
```

Result: `12 passed, 1 warning`

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

Result: `59 passed, 21 deselected, 1 warning`

### Recommended Fixes

1. In `get_approval_dashboard_items()`, bind approvals to the current stage explicitly.
   - At minimum add `ECOApproval.stage_id == ECO.stage_id`.
2. Pick one counting unit for `summary`.
   - Recommended: make headline counts derive from the same filtered pending approval set as `items`.
3. Add data-driven tests for:
   - prior-stage pending approvals are excluded
   - summary counts reconcile with item list counts
