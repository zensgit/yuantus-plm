# TODO - Phase 3 Tenant Import Rehearsal Toolchain Closeout

Date: 2026-04-29

## Documentation

- [x] Add closeout task MD.
- [x] Add DEV and verification MD.
- [x] Add closeout TODO MD.
- [x] Reconcile parent P3.4 TODO machine-gate items.
- [x] Keep external operator evidence unchecked.
- [x] Keep production cutover unchecked.
- [x] Update delivery doc index.

## Verification

- [x] Run P3.4 focused suite.
- [x] Run doc-index trio.
- [x] Run runbook/index contracts.
- [x] Run `git diff --check`.

## Still External

- [ ] Pilot tenant approved.
- [ ] Non-production PostgreSQL rehearsal DSNs available.
- [ ] Backup/restore owner named.
- [ ] Rehearsal window scheduled.
- [ ] Table classification artifact signed off.
- [ ] P3.4.1 dry-run report exists with `ready_for_import=true`.
- [ ] Operator-run PostgreSQL rehearsal evidence exists.
- [ ] Evidence gate accepts real operator evidence.
- [ ] Archive manifest exists for real evidence output.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
- [ ] Automatic rollback or destructive cleanup.
