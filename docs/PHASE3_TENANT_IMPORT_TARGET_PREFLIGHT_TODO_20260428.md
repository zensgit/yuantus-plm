# TODO - Phase 3 Tenant Import Target Preflight

Date: 2026-04-28

## Implementation

- [x] Add `yuantus.scripts.tenant_import_rehearsal_target_preflight`.
- [x] Require `--confirm-target-preflight` before opening a DB connection.
- [x] Validate the import plan before opening a DB connection.
- [x] Reject non-PostgreSQL target URLs before opening a DB connection.
- [x] Validate target schema identity against the plan.
- [x] Read target schema table inventory.
- [x] Validate `<schema>.alembic_version`.
- [x] Require all planned tenant tables to exist in the target schema.
- [x] Block global/control-plane tables in the target schema.
- [x] Emit JSON and Markdown reports.
- [x] Keep `ready_for_cutover=false`.

## Next-Action Gate

- [x] Add `--target-preflight-json`.
- [x] Add `run_target_preflight`.
- [x] Add `fix_target_preflight_report`.
- [x] Add `fix_target_preflight_blockers`.
- [x] Require green target preflight before `claude_required=true`.

## Documentation

- [x] Add target preflight taskbook.
- [x] Add development and verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Explicitly Not Started

- [ ] Implement `yuantus.scripts.tenant_import_rehearsal`.
- [ ] Export or import rows.
- [ ] Connect to a source database.
- [ ] Create, migrate, downgrade, drop, or clean up schemas.
- [ ] Enable `TENANCY_MODE=schema-per-tenant`.
- [ ] Perform production cutover.
