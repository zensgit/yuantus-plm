# TODO — Phase 3 Tenant Import Evidence Handoff

Date: 2026-04-29

## Implementation

- [x] Add DB-free evidence handoff gate CLI.
- [x] Read archive manifest JSON.
- [x] Read redaction guard JSON.
- [x] Require archive schema version.
- [x] Require `ready_for_archive=true`.
- [x] Require archive `ready_for_cutover=false`.
- [x] Require redaction guard schema version.
- [x] Require `ready_for_artifact_handoff=true`.
- [x] Require redaction guard `ready_for_cutover=false`.
- [x] Require redaction coverage for every archived artifact path.
- [x] Emit JSON and Markdown reports.
- [x] Keep `ready_for_cutover=false`.
- [x] Add focused tests.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODO.
- [x] Update delivery doc index.

## Verification

- [x] Evidence handoff focused tests pass.
- [x] Adjacent archive/redaction/status tests pass.
- [x] Full P3.4 focused suite passes.
- [x] Doc-index contracts pass.
- [x] Runbook/index contracts pass.
- [x] `py_compile` passes.
- [x] `git diff --check` is clean.

## Explicitly Not Started

- [ ] Run row-copy rehearsal.
- [ ] Generate real operator evidence.
- [ ] Run evidence gate against real operator evidence.
- [ ] Build real archive manifest.
- [ ] Run evidence handoff against real archive/redaction outputs.
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
