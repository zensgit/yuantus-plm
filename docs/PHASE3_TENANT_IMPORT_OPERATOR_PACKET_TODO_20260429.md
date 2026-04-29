# TODO - Phase 3 Tenant Import Operator Packet

Date: 2026-04-29

## Implementation

- [x] Add DB-free operator packet CLI.
- [x] Read implementation packet JSON.
- [x] Validate implementation packet schema and ready fields.
- [x] Fresh-validate the upstream next-action evidence chain.
- [x] Validate source and target DSN placeholder names.
- [x] Build row-copy rehearsal command.
- [x] Build operator evidence template command.
- [x] Build evidence gate command.
- [x] Build archive manifest command.
- [x] Emit JSON and Markdown packet reports.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Green implementation packet builds ordered commands.
- [x] Default artifact prefix uses target schema.
- [x] Invalid environment-variable names block.
- [x] Blocked implementation packet blocks.
- [x] Stale upstream artifact blocks.
- [x] CLI writes JSON and Markdown.
- [x] Strict CLI returns non-zero when blocked.
- [x] Source guard confirms operator-packet-only scope.

## Documentation

- [x] Add taskbook.
- [x] Add DEV and verification MD.
- [x] Add TODO MD.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODOs.
- [x] Update delivery doc index.

## Still External

- [ ] Run the generated packet against operator-provided non-production PostgreSQL DSNs.
- [ ] Run row-copy rehearsal.
- [ ] Capture operator evidence.
- [ ] Run evidence gate against real operator evidence.
- [ ] Run archive manifest generator against real evidence output.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
- [ ] Automatic rollback or destructive cleanup.
