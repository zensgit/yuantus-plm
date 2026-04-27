# TODO — Phase 3 Tenant Migration Dry-Run

Date: 2026-04-27

## Implementation

- [x] Implement pure report builder.
- [x] Implement CLI with JSON and Markdown output.
- [x] Redact source URL passwords in reports.
- [x] Generate FK-safe tenant import order.
- [x] Exclude global/control-plane tables from import candidates.
- [x] Fail closed on unknown source tables.
- [x] Treat `alembic_version` as allowed source metadata.

## Tests

- [x] Cover full tenant source with global table present.
- [x] Cover partial source row-count snapshot.
- [x] Cover missing tenant tables.
- [x] Cover unknown source table blockers.
- [x] Cover CLI JSON/Markdown output.
- [x] Cover `--strict` non-zero blocker exit.
- [x] Cover invalid source URL exit code 2.
- [x] Cover no target/schema creation commands in dry-run source.

## Documentation

- [x] Add Claude task MD.
- [x] Update tenant migration runbook with P3.4.1 dry-run section.
- [x] Add development and verification MD.
- [x] Update delivery doc index.

## Verification

- [x] Run focused pytest suite.
- [x] Run tenant baseline generator drift check.
- [x] Run app boot check.
- [x] Run `git diff --check`.
