# TODO - Phase 3 Tenant Import Rehearsal Scaffold

Date: 2026-04-28

## Implementation

- [x] Add `yuantus.scripts.tenant_import_rehearsal`.
- [x] Require implementation packet JSON.
- [x] Require `--confirm-rehearsal`.
- [x] Validate implementation packet schema and ready state.
- [x] Re-run fresh implementation-packet validation.
- [x] Block stale or tampered packet context.
- [x] Emit JSON scaffold report.
- [x] Emit Markdown scaffold report.
- [x] Use `ready_for_rehearsal_scaffold` as the primary pass/fail field.
- [x] Keep `import_executed=false`.
- [x] Keep `db_connection_attempted=false`.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Green packet plus confirmation passes the scaffold guard.
- [x] Missing confirmation blocks before import.
- [x] Blocked implementation packet blocks the scaffold.
- [x] Stale upstream artifact blocks the scaffold.
- [x] Tampered packet context blocks the scaffold.
- [x] CLI writes JSON and Markdown reports.
- [x] `--strict` exits 1 when blocked.
- [x] Source remains DB-free and mutation-free.

## Documentation

- [x] Add scaffold taskbook.
- [x] Add development and verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Explicitly Not Started

- [ ] Implement real row-copy execution.
- [ ] Connect to source or target databases.
- [ ] Import tenant rows.
- [ ] Compare post-import row counts from a live target.
- [ ] Add PostgreSQL integration import execution tests.
- [ ] Enable production cutover.
