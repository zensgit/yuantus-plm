# TODO - Phase 3 Tenant Import Rehearsal External Status

Date: 2026-04-29

## Implementation

- [x] Add DB-free external status CLI.
- [x] Read operator execution packet.
- [x] Validate operator packet schema and ready fields.
- [x] Derive expected downstream artifact paths from operator packet outputs.
- [x] Report current stage and next action.
- [x] Include next command for pending operator steps.
- [x] Treat missing future artifacts as pending, not blocking.
- [x] Treat malformed existing artifacts as blocking.
- [x] Require companion Markdown for generated JSON artifacts.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Green operator packet with no outputs reports row-copy next action.
- [x] Complete chain reports archive-ready status.
- [x] Invalid rehearsal JSON blocks.
- [x] Missing companion Markdown blocks.
- [x] Invalid operator packet blocks.
- [x] CLI writes JSON and Markdown.
- [x] Strict CLI allows pending next action.
- [x] Strict CLI returns non-zero for invalid existing artifact.
- [x] Source guard confirms external-status-only scope.

## Documentation

- [x] Add taskbook.
- [x] Add DEV and verification MD.
- [x] Add TODO MD.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODOs.
- [x] Update delivery doc index.

## Still External

- [ ] Run the generated operator packet against operator-provided non-production PostgreSQL DSNs.
- [ ] Run row-copy rehearsal.
- [ ] Capture operator evidence.
- [ ] Run evidence gate against real operator evidence.
- [ ] Run archive manifest generator against real evidence output.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
- [ ] Automatic rollback or destructive cleanup.
