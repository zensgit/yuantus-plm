# TODO — Phase 3 Tenant Import Rehearsal Handoff

Date: 2026-04-28

## Implementation

- [x] Add handoff report builder.
- [x] Add handoff CLI.
- [x] Validate readiness schema version.
- [x] Validate dry-run schema version.
- [x] Require `ready_for_import=true`.
- [x] Require `ready_for_rehearsal=true`.
- [x] Require readiness blockers to be empty.
- [x] Require tenant id, target schema, redacted target URL, and dry-run JSON.
- [x] Emit JSON and Markdown handoff reports.
- [x] Return 1 in `--strict` mode when Claude must not start.

## Tests

- [x] Ready readiness report generates `ready_for_claude=true`.
- [x] Not-ready readiness report blocks Claude.
- [x] Schema mismatch blocks Claude.
- [x] CLI writes JSON and Markdown.
- [x] `--strict` exits 1 when blocked.
- [x] Source does not connect or mutate databases.
- [x] Plaintext secrets are absent from generated reports.

## Documentation

- [x] Add Claude task MD.
- [x] Add DEV/verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Still Blocked

- [ ] Actual import rehearsal implementation.
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.

## Claude Start Rule

Claude can start the actual importer only after this command exits 0 and the
generated Markdown says `Claude can start: true`.
