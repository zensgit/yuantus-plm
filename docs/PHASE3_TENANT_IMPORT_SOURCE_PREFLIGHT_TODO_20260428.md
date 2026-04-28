# TODO - Phase 3 Tenant Import Source Preflight

Date: 2026-04-28

## Implementation

- [x] Add `yuantus.scripts.tenant_import_rehearsal_source_preflight`.
- [x] Require `--confirm-source-preflight` before opening a DB connection.
- [x] Validate the import plan before opening a DB connection.
- [x] Inspect source table inventory.
- [x] Inspect source column inventory.
- [x] Require planned tenant tables to exist in the source DB.
- [x] Require target metadata columns to exist in matching source tables.
- [x] Report source extra columns without blocking.
- [x] Emit JSON and Markdown reports.
- [x] Keep `ready_for_cutover=false`.

## Next-Action Gate

- [x] Add `--source-preflight-json`.
- [x] Add `run_source_preflight`.
- [x] Add `fix_source_preflight_report`.
- [x] Add `fix_source_preflight_blockers`.
- [x] Require green source preflight before target preflight.
- [x] Require green source and target preflight before `claude_required=true`.

## Documentation

- [x] Add source preflight taskbook.
- [x] Add development and verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Explicitly Not Started

- [ ] Implement `yuantus.scripts.tenant_import_rehearsal`.
- [ ] Export or import rows.
- [ ] Connect to a target database.
- [ ] Create, migrate, downgrade, drop, or clean up schemas.
- [ ] Enable `TENANCY_MODE=schema-per-tenant`.
- [ ] Perform production cutover.
