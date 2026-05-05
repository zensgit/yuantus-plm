# TODO — Phase 3 Tenant Import Full Closeout

Date: 2026-05-05

## Scope

- [x] Add one explicit full-closeout wrapper.
- [x] Require `--confirm-rehearsal`.
- [x] Require `--confirm-closeout`.
- [x] Chain operator sequence and evidence closeout.
- [x] Preserve `ready_for_cutover=false`.
- [x] Add shell tests with fake Python module dispatch.
- [x] Add runbook usage.
- [x] Add delivery script and doc index entries.

## Still External

- [ ] Operator supplies real non-production PostgreSQL source/target DSNs.
- [ ] Operator runs the wrapper in the rehearsal window.
- [ ] Reviewer checks generated reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Automatic rollback or destructive cleanup.
