# Parallel Breakage Helpdesk Latest Ticket Summary

## Date

2026-04-05

## Goal

Close the second implementation package from `Breakage Helpdesk Traceability Enhancement Audit` by projecting the latest helpdesk ticket summary onto incident-facing breakage surfaces.

## Scope

In scope:

- breakage incident list payload
- breakage incident export payloads (`json` / `csv` / `md`)
- breakage cockpit incident rows

Out of scope:

- schema changes
- migration changes
- new helpdesk sync lifecycle behavior
- new analytics or export surfaces

## Implemented Contract

The service now builds a per-incident latest helpdesk summary from the newest `breakage_helpdesk_sync_stub` job for each incident and projects it as `helpdesk_ticket_summary`.

Projected summary fields:

- `job_id`
- `job_status`
- `sync_status`
- `provider`
- `external_ticket_id`
- `provider_ticket_status`
- `provider_assignee`
- `provider_ticket_updated_at`
- `failure_category`
- `last_error`
- `updated_at`

## Surface Coverage

| Surface | Before | After |
| --- | --- | --- |
| `GET /breakages` | incident row had no latest helpdesk ticket projection | incident row includes `helpdesk_ticket_summary` |
| `GET /breakages/export?format=json` | export row had no latest ticket summary | nested `helpdesk_ticket_summary` included |
| `GET /breakages/export?format=csv` | no flattened latest ticket columns | flattened latest ticket columns included |
| `GET /breakages/export?format=md` | no latest ticket columns in table | ticket/provider/status/assignee/sync columns included |
| `GET /breakages/cockpit` | cockpit incident rows had no latest ticket projection | cockpit incident rows include `helpdesk_ticket_summary` |

## Write Set

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

## Notes

- No migration is required because the latest ticket summary is derived from existing helpdesk sync jobs.
- `helpdesk_sync_summary` aggregate payload remains unchanged; this package only adds row-level latest ticket projection.
- This package closes the remaining traceability gap identified after `breakage-incident-identity-and-dimensions`.

## Result

`breakage-helpdesk-latest-ticket-summary` is complete. Breakage incident row surfaces now expose both normalized incident identity/dimensions and latest helpdesk ticket context without additional API calls.
