# TODO — Phase 3 Tenant Import Operator Request

Date: 2026-04-29

## Implementation

- [x] Add DB-free operator request CLI.
- [x] Read external status JSON only.
- [x] Validate external status schema version.
- [x] Require `ready_for_external_progress=true`.
- [x] Require `ready_for_cutover=false`.
- [x] Reject blocked external status.
- [x] Map each pending stage to required operator inputs.
- [x] Preserve next command from external status.
- [x] Keep archive-ready state as review-only with no next command.
- [x] Render JSON and Markdown outputs.
- [x] Add focused tests.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Verification

- [x] Operator request focused tests pass.
- [x] External status and operator packet regression tests pass.
- [x] Doc-index contracts pass.
- [x] Runbook index contracts pass.
- [x] `py_compile` passes.
- [x] `git diff --check` is clean.

## Explicitly Not Started

- [ ] Run row-copy rehearsal.
- [ ] Generate real operator evidence.
- [ ] Run evidence gate against real operator evidence.
- [ ] Build real archive manifest.
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
