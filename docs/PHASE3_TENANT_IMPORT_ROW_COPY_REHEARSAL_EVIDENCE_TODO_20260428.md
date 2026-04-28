# TODO - Phase 3 Tenant Import Row-Copy Rehearsal Evidence

Date: 2026-04-28

## Implementation

- [x] Add offline rehearsal evidence CLI.
- [x] Read row-copy rehearsal JSON.
- [x] Read implementation packet JSON.
- [x] Read operator evidence Markdown.
- [x] Validate rehearsal schema and success flags.
- [x] Validate implementation packet schema and context match.
- [x] Fresh-revalidate upstream artifacts from `next_action_json`.
- [x] Validate table-level row-count matches.
- [x] Reject global/control-plane table results.
- [x] Validate operator evidence sign-off fields.
- [x] Redact rehearsal DB URL in outputs.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Green evidence path passes.
- [x] Missing operator evidence blocks.
- [x] Missing sign-off fields block.
- [x] Tenant and rehearsal DB mismatch blocks.
- [x] Blocked rehearsal report blocks.
- [x] Row-count mismatch blocks.
- [x] Global/control-plane table leakage blocks.
- [x] Implementation packet mismatch blocks.
- [x] Stale upstream artifact blocks.
- [x] CLI writes JSON and Markdown.
- [x] Strict mode exits non-zero when blocked.
- [x] Source guard confirms the evidence gate is offline.

## Documentation

- [x] Add taskbook.
- [x] Add DEV and verification MD.
- [x] Add TODO MD.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODOs.
- [x] Update delivery doc index.

## Still External

- [ ] Run row-copy rehearsal against operator-provided non-production PostgreSQL DSNs.
- [ ] Archive real rehearsal JSON and Markdown evidence.
- [ ] Run evidence gate against real rehearsal outputs.
- [ ] Review evidence with the named backup/restore owner.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
- [ ] Automatic rollback or destructive cleanup.
