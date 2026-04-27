# TODO — Phase 3 Tenant Import Rehearsal

Date: 2026-04-27

## Stop Gate

- [ ] Pilot tenant approved.
- [ ] Non-production PostgreSQL rehearsal DSN available.
- [ ] Backup/restore owner named.
- [ ] Rehearsal window scheduled.
- [ ] Table classification artifact signed off.
- [ ] P3.4.1 dry-run report exists with `ready_for_import=true`.

## Taskbook PR

- [x] Define import rehearsal scope.
- [x] Define required external inputs.
- [x] Define future CLI.
- [x] Define future result shape.
- [x] Define fail-closed blockers.
- [x] Define future test matrix.
- [x] Add verification MD.
- [x] Update delivery doc index.

## Future Implementation PR

- [ ] Implement `yuantus.scripts.tenant_import_rehearsal`.
- [ ] Require `--confirm-rehearsal`.
- [ ] Validate dry-run JSON before DB connections.
- [ ] Validate target PostgreSQL schema and alembic version.
- [ ] Import only `tenant_tables_in_import_order`.
- [ ] Block all global/control-plane tables.
- [ ] Emit JSON and Markdown rehearsal reports.
- [ ] Add PostgreSQL integration tests guarded by `YUANTUS_TEST_PG_DSN`.
- [ ] Update `RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- [ ] Add DEV/verification MD for the implementation PR.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Data import into any production database.
- [ ] Automatic rollback or destructive cleanup.
