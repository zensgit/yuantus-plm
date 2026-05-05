# TODO — Phase 3 Tenant Import Operator Command Pack

Date: 2026-05-05

## Scope

- [x] Add a DB-free command-pack shell wrapper.
- [x] Require precheck success before writing the command file.
- [x] Keep DSN values hidden.
- [x] Preserve `ready_for_cutover=false`.
- [x] Add focused shell tests.
- [x] Add runbook usage.
- [x] Add delivery script and doc index entries.

## Still External

- [ ] Run the real operator PostgreSQL rehearsal.
- [ ] Complete operator evidence with non-placeholder sign-off fields.
- [ ] Run evidence closeout on the real evidence artifacts.
- [ ] Produce final reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Data import into any production database.
- [ ] Automatic rollback or destructive cleanup.
