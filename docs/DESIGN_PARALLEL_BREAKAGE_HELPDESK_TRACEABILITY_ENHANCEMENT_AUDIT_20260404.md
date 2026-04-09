# Design: Breakage Helpdesk Traceability Enhancement Audit

## Date

2026-04-04

## Scope

Audit current breakage incident + helpdesk sync surfaces to determine the
remaining Odoo18-inspired development needed for traceability parity:

- A2 grouped counters by `bom_id` / `mbom_id` / `routing_id`
- A1 bidirectional/latest helpdesk ticket trace on incident-facing surfaces
- A3 human-readable incident sequence / code

This is an audit-first package only. No code changes are required for this
document.

## Current Capabilities (already implemented)

| Capability | Status | Evidence |
|-----------|:------:|---------|
| Breakage incident create/list/export surfaces | YES | `POST /breakages`, `GET /breakages`, `GET /breakages/export` |
| Breakage cockpit + export | YES | `GET /breakages/cockpit`, `GET /breakages/cockpit/export` |
| Metrics groups + export | YES | `GET /breakages/metrics/groups`, `GET /breakages/metrics/groups/export` |
| Status update flow | YES | `POST /breakages/{incident_id}/status` |
| Helpdesk sync lifecycle | YES | enqueue + status + execute + result + ticket-update |
| Provider ticket state tracking | YES | `external_ticket_id`, `provider_ticket_status`, `provider_event_ids`, assignee, payload |
| Export job workflow | YES | breakage export jobs create/get/download/cleanup |
| Parallel-ops failure triage / replay / export | YES | failure triage, replay batches, replay trends, export jobs |
| Existing grouping dimensions | PARTIAL | `product_item_id`, `batch_code`, `bom_line_item_id`, `mbom_id`, `responsibility`, `routing_id` |

## Audit Matrix

| Surface | Contract object | Target | Scope | Current status | Gap? | Gap type | Fix needed |
|---------|-----------------|--------|-------|----------------|:----:|----------|------------|
| Incident create/list/export | breakage incident core contract | First-class `bom_id` / `mbom_id` / `routing_id` + stable display id | create/list/export | PARTIAL | YES | medium code | Normalize incident dimensions and response fields |
| Cockpit rows + cockpit export | breakage operator view | Same normalized dimensions on operator-facing rows | cockpit/export | PARTIAL | YES | medium code | Reuse normalized incident serializer in cockpit |
| Metrics groups | grouped counters | Real grouping by `bom_id` / `mbom_id` / `routing_id` | groups/export | PARTIAL | YES | medium code | Stop aliasing `mbom_id -> version_id` and `routing_id -> production_order_id`; add `bom_id` |
| Helpdesk sync status surfaces | latest ticket state | Current provider/job state for one incident | status/execute/result/ticket-update | COMPLETE | NO | — | — |
| Incident-facing helpdesk projection | latest ticket summary on incident rows | Latest ticket id/status/provider/assignee on list/export/cockpit | incident/cockpit/export | PARTIAL | YES | medium code | Project latest helpdesk summary onto incident-facing rows |
| Incident identity | human-readable incident sequence | `incident_code` / stable display code | create/list/export/cockpit | ABSENT | YES | medium code | Add generated incident code |
| Parallel-ops helpdesk failure triage | failure operations | helpdesk failure backlog review/export/replay | triage/replay/export | COMPLETE | NO | — | — |

## Real Gaps

### GAP-T1: Incident dimensions are not normalized to the public contract

The breakage model still stores:

- `version_id` instead of first-class `mbom_id`
- `production_order_id` instead of first-class `routing_id`
- no `bom_id` at all

The public metrics-groups API already advertises `mbom_id` and `routing_id`,
but the service currently aliases them:

- `mbom_id -> version_id`
- `routing_id -> production_order_id`

That means the surface looks richer than the underlying incident contract
really is. This is a real contract gap, not just a docs problem.

### GAP-T2: No human-readable incident code

Incidents have UUID `id` and optional `batch_code`, but no stable display-grade
`incident_code`. For operator workflows and external handoff, this is weaker
than the intended parity target.

### GAP-T3: Latest helpdesk ticket summary is not projected onto incident rows

Helpdesk status surfaces already know the latest:

- `external_ticket_id`
- provider
- provider ticket status
- assignee
- event ids / update timestamps

But core incident list/export/cockpit rows do not expose that summary. Operators
must jump to `helpdesk-sync/status` per incident, which breaks traceability at
the main review surface.

## What Is Already Good Enough

- Core breakage CRUD-lite flow is present and tested.
- Helpdesk sync lifecycle is present and tested.
- Failure triage / replay / export surfaces are already strong.
- Export coverage already exists for incident/cockpit/grouping/failure-review
  flows.

This line is therefore **not** a greenfield product build. It is a focused
contract-normalization + projection enhancement.

## Classification

### **CODE-CHANGE CANDIDATE**

This line is not docs-only.

The remaining work is medium-sized, bounded, and concentrated in the breakage
incident contract:

1. normalize incident dimensions
2. add incident display identity
3. project latest helpdesk ticket summary onto incident-facing rows

No large architecture rewrite is needed, but at least one model/schema change
is likely.

## Minimum Write Set

### Package 1: `breakage-incident-identity-and-dimensions`

Scope:

- add first-class `bom_id`
- add first-class `mbom_id`
- add first-class `routing_id`
- add generated `incident_code`
- update create/list/export/cockpit/grouping contracts

Likely files:

- `src/yuantus/meta_engine/models/parallel_tasks.py`
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- breakage service/router tests

Estimated size: medium
Risk: medium
Likely requires migration: yes

### Package 2: `breakage-helpdesk-latest-ticket-summary`

Scope:

- project latest helpdesk summary onto incident list/export/cockpit rows
- keep existing per-incident helpdesk status surfaces unchanged

Likely files:

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- breakage service/router tests

Estimated size: small-medium
Risk: low-medium
Likely requires migration: no

## Recommended Order

1. `breakage-incident-identity-and-dimensions`
2. `breakage-helpdesk-latest-ticket-summary`

Reason:

- ticket summary projection should land on top of the normalized incident
  contract, not the current alias-heavy contract
- the identity/dimension package closes A2 + A3
- the summary projection package closes the remaining A1-facing operator gap

## Closure Verdict

This line is **not closed yet**.

It is a bounded, medium-sized contract enhancement line with 2 reasonable
implementation packages. The current system already has strong breakage/helpdesk
operations coverage, but traceability parity still needs:

- normalized incident dimensions
- human-readable incident identity
- row-level latest ticket summary projection
