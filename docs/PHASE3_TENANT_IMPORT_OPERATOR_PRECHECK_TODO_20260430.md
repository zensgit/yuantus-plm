# TODO — Phase 3 Tenant Import Operator Precheck

Date: 2026-04-30

## Done

- [x] Add `scripts/precheck_tenant_import_rehearsal_operator.sh`.
- [x] Validate implementation packet existence.
- [x] Validate implementation packet green state.
- [x] Validate `ready_for_cutover=false`.
- [x] Validate source and target DSN env vars are set without printing values.
- [x] Validate required helper scripts are executable.
- [x] Add focused precheck tests.
- [x] Add shell syntax/index contract coverage.
- [x] Add runbook pointer.
- [x] Add development and verification docs.
- [x] Add delivery-doc index entries.

## Not Done

- [ ] Run operator PostgreSQL row-copy rehearsal.
- [ ] Create or sign operator evidence.
- [ ] Build real evidence closeout artifacts.
- [ ] Mark P3.4 stop gate complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
