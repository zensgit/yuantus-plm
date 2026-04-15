# P2 ECO Approval Routing MVP

Date: 2026-04-15

## Recommendation
- Do **not** start with a new `ApprovalTemplate + ApprovalRule + RoutingService` stack.
- Current mainline already has:
  - ECO stage-level approval config (`approval_roles`, `min_approvals`, `sla_hours`)
  - pending/overdue approval APIs
  - a separate generic approvals domain
- The bounded next step is a canonical ECO approval-routing read surface that exposes who can approve the current stage and how far the stage is from completion.

## Changes
- `src/yuantus/meta_engine/services/eco_service.py`
  - Added `ECOApprovalService.get_approval_routing(...)`
  - Added candidate approver resolution from current `ECOStage.approval_roles`
  - Added routing summary output: explicit role-based vs open routing, candidate users, approval progress, remaining approvals, overdue state
- `src/yuantus/meta_engine/web/eco_router.py`
  - Added `GET /api/v1/eco/{eco_id}/approval-routing`
- `src/yuantus/meta_engine/tests/test_eco_approval_routing.py`
  - Added focused service/router contract coverage

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_eco_approval_routing.py src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/web/eco_router.py src/yuantus/meta_engine/tests/test_eco_approval_routing.py`

## Observed Result
- `18 passed, 1 warning`
- `py_compile` passed
- No full-repo regression was run locally for this slice
