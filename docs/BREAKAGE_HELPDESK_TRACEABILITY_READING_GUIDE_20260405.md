# Breakage Helpdesk Traceability Enhancement — Reading Guide

## Date

2026-04-05

## Who this is for

An engineer or reviewer encountering the breakage/helpdesk traceability line
for the first time.

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — closure state, fixed gaps, remaining blockers
2. **Traceability Audit Design** — original gap matrix and package split

### Full implementation path (6 docs, ~20 min)

1. Final Summary (design + verification)
2. Traceability Audit (design + verification)
3. Incident Identity and Dimensions (design + verification)
4. Latest Ticket Summary (design + verification)

## Document Map by Topic

### 1. Final Summary & Closure

*Answers: "Is the line closed? What exactly was fixed?"*

| Doc | Path |
| --- | --- |
| Final Summary Design | `docs/DESIGN_PARALLEL_BREAKAGE_HELPDESK_TRACEABILITY_FINAL_SUMMARY_20260405.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_BREAKAGE_HELPDESK_TRACEABILITY_FINAL_SUMMARY_20260405.md` |
| Traceability Audit Design | `docs/DESIGN_PARALLEL_BREAKAGE_HELPDESK_TRACEABILITY_ENHANCEMENT_AUDIT_20260404.md` |
| Traceability Audit Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_BREAKAGE_HELPDESK_TRACEABILITY_ENHANCEMENT_AUDIT_20260404.md` |

### 2. Incident Identity and Dimensions

*Answers: "How were incident_code / bom_id / mbom_id / routing_id normalized?"*

| Doc | Path |
| --- | --- |
| Package Design | `docs/DESIGN_PARALLEL_BREAKAGE_INCIDENT_IDENTITY_AND_DIMENSIONS_20260404.md` |
| Package Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_BREAKAGE_INCIDENT_IDENTITY_AND_DIMENSIONS_20260404.md` |

### 3. Latest Helpdesk Ticket Summary

*Answers: "How did latest ticket data get onto incident rows?"*

| Doc | Path |
| --- | --- |
| Package Design | `docs/DESIGN_PARALLEL_BREAKAGE_HELPDESK_LATEST_TICKET_SUMMARY_20260405.md` |
| Package Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_BREAKAGE_HELPDESK_LATEST_TICKET_SUMMARY_20260405.md` |

## Surface Guide

### Breakage Incident List / Export

Use the latest ticket summary package to understand how:

- `GET /breakages`
- `GET /breakages/export`

now expose both normalized incident identity and latest helpdesk ticket
context.

### Breakage Cockpit

Use the latest ticket summary package plus the audit to understand how cockpit
incident rows gained latest helpdesk ticket context without changing aggregate
`helpdesk_sync_summary`.

### Metrics Groups

Use the incident identity and dimensions package to understand how `bom_id`
became a first-class grouped dimension and how `mbom_id` / `routing_id`
stopped being alias-only public fields.

### Helpdesk Lifecycle

Use the audit to understand what was already complete before the two closure
packages:

- enqueue
- status
- execute
- result
- ticket-update
- failure triage / replay / export

## Key Source Files

| File | Role |
| --- | --- |
| `src/yuantus/meta_engine/models/parallel_tasks.py` | Breakage incident contract |
| `src/yuantus/meta_engine/services/parallel_tasks_service.py` | Incident normalization, exports, cockpit, latest helpdesk summary |
| `src/yuantus/meta_engine/web/parallel_tasks_router.py` | Breakage create/list/export/cockpit router contract |

## Key Test Files

| File | Coverage |
| --- | --- |
| `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py` | Breakage service export, cockpit, helpdesk lifecycle |
| `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py` | Breakage router list/export/cockpit contract |
| `src/yuantus/meta_engine/tests/test_breakage_tasks.py` | Task execution and helpdesk sync worker coverage |

## Remaining Items

No known blocking gaps remain for the breakage/helpdesk traceability
enhancement line.
