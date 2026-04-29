# TODO - Phase 3 Tenant Import Rehearsal Evidence Template

Date: 2026-04-29

## Implementation

- [x] Add DB-free operator evidence template CLI.
- [x] Read row-copy rehearsal JSON.
- [x] Require green rehearsal status before ready output.
- [x] Fill tenant ID from rehearsal report.
- [x] Fill redacted non-production rehearsal DB from rehearsal report.
- [x] Require backup/restore owner under `--strict`.
- [x] Require rehearsal window under `--strict`.
- [x] Require operator and reviewer under `--strict`.
- [x] Require pass result under `--strict`.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Complete template is parseable by evidence gate parser.
- [x] Missing operator fields block and render placeholders.
- [x] Blocked rehearsal report blocks ready output.
- [x] Non-pass rehearsal result blocks.
- [x] CLI writes JSON and Markdown.
- [x] Strict CLI returns non-zero when incomplete.
- [x] Source guard confirms template-only scope.

## Documentation

- [x] Add taskbook.
- [x] Add DEV and verification MD.
- [x] Add TODO MD.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODOs.
- [x] Update delivery doc index.

## Still External

- [ ] Run row-copy rehearsal against operator-provided non-production PostgreSQL DSNs.
- [ ] Generate real operator evidence Markdown.
- [ ] Run evidence gate against the real operator evidence.
- [ ] Archive real rehearsal evidence outputs.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
- [ ] Automatic rollback or destructive cleanup.
