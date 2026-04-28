# TODO - Phase 3 Tenant Import Packet Integrity

Date: 2026-04-28

## Implementation

- [x] Require every next-action artifact path to exist.
- [x] Validate each artifact as a JSON object.
- [x] Validate schema versions for dry-run, readiness, handoff, plan, source
  preflight, and target preflight.
- [x] Validate each artifact's ready flag.
- [x] Validate every artifact has no blockers.
- [x] Validate tenant and target schema consistency.
- [x] Include artifact-integrity rows in the Markdown packet.

## Tests

- [x] Green artifacts generate `ready_for_claude_importer=true`.
- [x] Missing artifact path blocks the packet.
- [x] Missing artifact file blocks the packet.
- [x] Blocked artifact blocks the packet.
- [x] Tenant/schema mismatch blocks the packet.
- [x] CLI writes JSON and Markdown with artifact integrity.
- [x] Source remains DB-free and mutation-free.

## Documentation

- [x] Add packet-integrity taskbook.
- [x] Add development and verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Explicitly Not Started

- [ ] Implement `yuantus.scripts.tenant_import_rehearsal`.
- [ ] Export or import rows.
- [ ] Connect to source or target databases.
- [ ] Create, migrate, downgrade, drop, or clean up schemas.
- [ ] Enable `TENANCY_MODE=schema-per-tenant`.
- [ ] Perform production cutover.
