# TODO - Phase 3 Tenant Import Rehearsal Evidence Archive

Date: 2026-04-29

## Implementation

- [x] Add DB-free archive manifest CLI.
- [x] Read accepted evidence report.
- [x] Follow implementation packet upstream artifact paths.
- [x] Include optional operator evidence template JSON.
- [x] Validate JSON schema versions.
- [x] Validate ready fields.
- [x] Validate `ready_for_cutover=false`.
- [x] Emit SHA-256 digest for every artifact.
- [x] Emit JSON and Markdown manifests.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Green chain builds archive manifest with hashes.
- [x] Archive can omit template JSON for hand-written evidence.
- [x] Blocked evidence report blocks archive.
- [x] Missing artifact blocks archive.
- [x] Schema and ready-field drift blocks archive.
- [x] Template `output_md` mismatch blocks archive.
- [x] CLI writes JSON and Markdown.
- [x] Strict CLI returns non-zero when blocked.
- [x] Source guard confirms archive-only scope.

## Documentation

- [x] Add taskbook.
- [x] Add DEV and verification MD.
- [x] Add TODO MD.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODOs.
- [x] Add operator execution packet follow-up.
- [x] Update delivery doc index.

## Still External

- [ ] Run row-copy rehearsal against operator-provided non-production PostgreSQL DSNs.
- [ ] Run evidence template generator against real rehearsal output.
- [ ] Run evidence gate against real operator evidence.
- [ ] Run archive manifest generator against real evidence output.
- [ ] Archive the real manifest and referenced artifacts.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
- [ ] Automatic rollback or destructive cleanup.
