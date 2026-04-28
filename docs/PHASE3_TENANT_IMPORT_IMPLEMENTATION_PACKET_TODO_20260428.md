# TODO - Phase 3 Tenant Import Implementation Packet

Date: 2026-04-28

## Implementation

- [x] Add `yuantus.scripts.tenant_import_rehearsal_implementation_packet`.
- [x] Require green next-action schema and state.
- [x] Require `claude_required=true`.
- [x] Require no next-action blockers.
- [x] Require dry-run/readiness/handoff/plan/source-preflight/target-preflight
  evidence paths.
- [x] Emit JSON packet.
- [x] Emit Claude task Markdown packet.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Green next-action generates `ready_for_claude_importer=true`.
- [x] Non-final next-action blocks the packet.
- [x] Missing artifact paths block the packet.
- [x] CLI writes JSON and Markdown.
- [x] `--strict` exits 1 when blocked.
- [x] Source does not connect or mutate databases.

## Documentation

- [x] Add implementation packet taskbook.
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
