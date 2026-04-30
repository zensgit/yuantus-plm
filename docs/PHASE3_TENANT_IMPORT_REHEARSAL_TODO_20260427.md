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

- [x] Implement real row-copy execution behind `tenant_import_rehearsal`.
- [x] Require a green Claude handoff report before starting.
- [x] Require next-action report with `claude_required=true`.
- [x] Require import plan report with `ready_for_importer=true`.
- [x] Require source preflight report with `ready_for_importer_source=true`.
- [x] Require target preflight report with `ready_for_importer_target=true`.
- [x] Require implementation packet with `ready_for_claude_importer=true`.
- [x] Require `--confirm-rehearsal`.
- [x] Validate dry-run JSON before DB connections.
- [x] Validate target PostgreSQL schema and alembic version.
- [x] Import only `tenant_tables_in_import_order`.
- [x] Block all global/control-plane tables.
- [x] Emit JSON and Markdown scaffold reports.
- [x] Emit JSON and Markdown row-import rehearsal reports.
- [x] Add offline operator-run rehearsal evidence validator.
- [x] Add operator evidence Markdown template generator.
- [x] Add rehearsal evidence archive manifest generator.
- [x] Add operator execution packet generator.
- [x] Add external operator progress status checker.
- [x] Reconcile P3.4 toolchain closeout status.
- [x] Add operator request packet for external action handoff.
- [x] Add artifact redaction guard before evidence handoff.
- [x] Add evidence handoff gate tying archive and redaction coverage.
- [x] Add synthetic operator drill for DB-free command-path rehearsal.
- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [x] Update `RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- [x] Add DEV/verification MD for the implementation PR.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Data import into any production database.
- [ ] Automatic rollback or destructive cleanup.
