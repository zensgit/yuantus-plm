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

## Handoff Gate PR

- [x] Add readiness validator.
- [x] Add classification Sign-Off guard.
- [x] Add Claude handoff generator.
- [x] Require `ready_for_claude=true` before actual importer work starts.
- [x] Add next-action report to tell when Claude development is required.
- [x] Add import rehearsal plan manifest before actual importer work starts.
- [x] Add source preflight before actual importer work starts.
- [x] Add target preflight before actual importer work starts.
- [x] Add final Claude implementation packet before actual importer work starts.
- [x] Validate implementation packet upstream artifact existence and green state.
- [x] Add fail-closed `tenant_import_rehearsal` scaffold before row-copy work.

## Future Implementation PR

- [ ] Implement real row-copy execution behind `tenant_import_rehearsal`.
- [ ] Require a green Claude handoff Markdown before starting.
- [ ] Require next-action report with `claude_required=true`.
- [ ] Require import plan report with `ready_for_importer=true`.
- [ ] Require source preflight report with `ready_for_importer_source=true`.
- [ ] Require target preflight report with `ready_for_importer_target=true`.
- [x] Require implementation packet with `ready_for_claude_importer=true`.
- [x] Require `--confirm-rehearsal`.
- [x] Validate dry-run JSON before DB connections.
- [ ] Validate target PostgreSQL schema and alembic version.
- [ ] Import only `tenant_tables_in_import_order`.
- [ ] Block all global/control-plane tables.
- [x] Emit JSON and Markdown scaffold reports.
- [ ] Emit JSON and Markdown row-import rehearsal reports.
- [ ] Add PostgreSQL integration tests guarded by `YUANTUS_TEST_PG_DSN`.
- [ ] Update `RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- [ ] Add DEV/verification MD for the implementation PR.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Data import into any production database.
- [ ] Automatic rollback or destructive cleanup.
