# TODO — Phase 3 Tenant Import Evidence Intake

Date: 2026-04-30

## Implementation

- [x] Add DB-free evidence intake script.
- [x] Read operator packet outputs.
- [x] Require all expected artifact paths.
- [x] Validate rehearsal, template, evidence, and archive JSON schemas.
- [x] Validate ready fields and `ready_for_cutover=false`.
- [x] Reject synthetic drill JSON artifacts.
- [x] Reject synthetic drill Markdown artifacts.
- [x] Run redaction guard against the artifact set.
- [x] Emit JSON and Markdown intake reports.

## Tests

- [x] Green evidence artifact set is intake-ready.
- [x] Missing artifact blocks intake.
- [x] Synthetic JSON blocks intake.
- [x] Synthetic Markdown blocks intake.
- [x] Plaintext PostgreSQL password blocks without leaking secret.
- [x] CLI writes JSON and Markdown.
- [x] CLI strict mode exits 1 when blocked.
- [x] Source contract preserves DB-free intake-only scope.

## Docs

- [x] Add development task MD.
- [x] Add verification MD.
- [x] Add runbook section.
- [x] Update parent P3.4 TODO.
- [x] Update delivery doc index.

## Explicitly Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Accept evidence for reviewer handoff.
- [ ] Build archive manifest.
- [ ] Run the evidence handoff gate.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
