# TODO — Phase 3 Tenant Import Redaction Guard

Date: 2026-04-29

## Implementation

- [x] Add DB-free artifact redaction guard CLI.
- [x] Accept repeated `--artifact` paths.
- [x] Require artifacts to exist and be readable.
- [x] Detect PostgreSQL URLs in JSON/Markdown text.
- [x] Block unredacted PostgreSQL passwords.
- [x] Allow explicit redaction tokens such as `***` and `<redacted>`.
- [x] Keep blocker output redacted.
- [x] Emit JSON and Markdown reports.
- [x] Keep `ready_for_cutover=false`.
- [x] Add focused tests.
- [x] Update tenant migration runbook.
- [x] Update parent P3.4 TODO.
- [x] Update delivery doc index.

## Verification

- [x] Redaction guard focused tests pass.
- [x] Adjacent P3.4 artifact/evidence tests pass.
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
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Production data import.
