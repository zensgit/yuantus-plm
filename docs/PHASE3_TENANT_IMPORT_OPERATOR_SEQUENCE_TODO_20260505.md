# TODO — Phase 3 Tenant Import Operator Sequence

Date: 2026-05-05

## Scope

- [x] Add one explicit operator sequence wrapper.
- [x] Require `--confirm-rehearsal`.
- [x] Reuse source/target DSN environment variable names.
- [x] Chain precheck, launchpack, row-copy, evidence template, and evidence precheck.
- [x] Preserve `ready_for_cutover=false`.
- [x] Add shell tests with fake Python module dispatch.
- [x] Add runbook usage.
- [x] Add delivery script and doc index entries.

## Still External

- [ ] Operator supplies real non-production PostgreSQL source/target DSNs.
- [ ] Operator runs the wrapper in the rehearsal window.
- [ ] Operator reviews generated evidence Markdown.
- [ ] Operator runs evidence closeout after evidence precheck is green.

## Explicit Non-Goals

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Reviewer-packet generation inside this wrapper.
- [ ] Automatic rollback or destructive cleanup.
