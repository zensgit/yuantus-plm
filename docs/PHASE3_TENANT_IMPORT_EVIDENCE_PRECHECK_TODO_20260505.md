# TODO — Phase 3 Tenant Import Evidence Precheck

Date: 2026-05-05

## Scope

- [x] Add a DB-free evidence-precheck shell wrapper.
- [x] Reuse the existing evidence validator.
- [x] Fail closed before evidence closeout when operator evidence is missing or invalid.
- [x] Keep DSN values hidden.
- [x] Preserve `ready_for_cutover=false`.
- [x] Add focused shell tests.
- [x] Add runbook usage.
- [x] Add delivery script and doc index entries.

## Still External

- [ ] Run the real operator PostgreSQL rehearsal.
- [ ] Complete operator evidence with non-placeholder sign-off fields.
- [ ] Run evidence closeout after this precheck is green.
- [ ] Produce final reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Data import into any production database.
- [ ] Automatic rollback or destructive cleanup.
