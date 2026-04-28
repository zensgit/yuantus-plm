# TODO — Phase 3 Tenant Import Next Action

Date: 2026-04-28

## Implementation

- [x] Add next-action report builder.
- [x] Add next-action CLI.
- [x] Detect missing P3.4.1 dry-run report.
- [x] Detect dry-run blockers.
- [x] Detect missing P3.4.2 readiness report.
- [x] Detect readiness blockers.
- [x] Detect missing Claude handoff report.
- [x] Detect handoff blockers.
- [x] Set `claude_required=true` only for green handoff.
- [x] Return 1 in `--strict` mode until Claude is required.

## Tests

- [x] Missing dry-run points to `run_p3_4_1_dry_run`.
- [x] Dry-run blockers point to `fix_dry_run_blockers`.
- [x] Ready dry-run without readiness points to stop-gate collection.
- [x] Ready readiness without handoff points to `run_claude_handoff`.
- [x] Green handoff points to `ask_claude_to_implement_importer`.
- [x] CLI writes JSON and Markdown.
- [x] `--strict` exits 1 until Claude is required.
- [x] `--strict` exits 0 when Claude is required.
- [x] Source does not connect or mutate databases.

## Documentation

- [x] Add Claude task MD.
- [x] Add DEV/verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Notification Rule

Notify the user to let Claude implement the actual importer only when:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```
