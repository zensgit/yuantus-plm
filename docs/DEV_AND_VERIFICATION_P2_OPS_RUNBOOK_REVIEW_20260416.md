## P2 Ops Runbook Review

Date: 2026-04-16

### Conclusion

Do not sign off this runbook as-is. It has one documentation blocker and one operational gap.

### Findings

1. High: the runbook lists `GET /eco/{id}/approval-routing` as an existing operational endpoint, but this endpoint does not exist in the current source tree.
   - Runbook:
     - `docs/P2_OPS_RUNBOOK.md:12`
   - Source review:
     - no `approval-routing` route implementation found under `src/yuantus/meta_engine/web/eco_router.py`
     - repo-wide search only finds the string in docs, not in runtime code

2. Medium: the example `curl` commands omit authentication context for write endpoints that now require authenticated actors.
   - Runbook:
     - `docs/P2_OPS_RUNBOOK.md:35-36`
   - Runtime:
     - `POST /api/v1/eco/approvals/escalate-overdue` uses `Depends(get_current_user_id)`
     - `POST /api/v1/eco/{eco_id}/auto-assign-approvers` also uses `Depends(get_current_user_id)`
   - Impact:
     - copy/paste operations guidance will fail with `401` unless auth headers or equivalent session context are included

### What Was Verified

1. The documented dashboard/export/audit endpoints do exist in the router:
   - `/api/v1/eco/approvals/dashboard/summary`
   - `/api/v1/eco/approvals/dashboard/items`
   - `/api/v1/eco/approvals/dashboard/export`
   - `/api/v1/eco/approvals/audit/anomalies`
   - `/api/v1/eco/approvals/escalate-overdue`
   - `/api/v1/eco/{eco_id}/auto-assign-approvers`

2. Delivery document names listed in the runbook appear to exist locally.

### Recommended Fix

1. Remove or correct the `approval-routing` line unless the endpoint is reintroduced.
2. Update the `curl` examples to include the required auth context, or explicitly state that they assume an authenticated session/token.
