# TODO — Phase 3 Tenant Import Rehearsal Plan

Date: 2026-04-28

## Implementation

- [x] Add import plan report builder.
- [x] Add import plan CLI.
- [x] Validate dry-run schema version.
- [x] Validate handoff schema version.
- [x] Require dry-run `ready_for_import=true`.
- [x] Require handoff `ready_for_claude=true`.
- [x] Require both blocker lists to be empty.
- [x] Require tenant id and target schema to match.
- [x] Reject global/control-plane tables in import order.
- [x] Require row-count coverage to exactly match import order.
- [x] Keep `ready_for_cutover=false`.
- [x] Update next-action to require a green plan before Claude starts.

## Tests

- [x] Ready inputs generate `ready_for_importer=true`.
- [x] Handoff blockers block the plan.
- [x] Global table in import order blocks the plan.
- [x] Row-count mismatch blocks the plan.
- [x] Tenant/schema mismatch blocks the plan.
- [x] CLI writes JSON and Markdown.
- [x] `--strict` exits 1 when blocked.
- [x] Source does not connect or mutate databases.

## Documentation

- [x] Add Claude task MD.
- [x] Add DEV/verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.
- [x] Update next-action docs to include the plan gate.

## Still Blocked

- [ ] Actual import rehearsal implementation.
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
