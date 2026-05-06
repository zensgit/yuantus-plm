# TODO - Phase 3 Tenant Import Command Validator CLI Error Redaction

Date: 2026-05-05

## Scope

- [x] Stop echoing unknown CLI argument values.
- [x] Stop echoing missing command-file paths.
- [x] Preserve exit code `2` for CLI parse/input errors.
- [x] Preserve usage output for unknown arguments.
- [x] Cover DSN-like unknown argument values.
- [x] Cover DSN-like missing command-file paths.
- [x] Update runbook and readiness tracking.
- [x] Keep parent P3.4 operator-run evidence item unchecked.
- [x] Add verification MD and delivery-doc index entries.

## Explicitly Still External

- [ ] Operator fills a repo-external env file with real non-production DSNs.
- [ ] Operator runs the PostgreSQL rehearsal during the approved window.
- [ ] Reviewer accepts real operator evidence.

## Explicit Non-Goals

- [ ] Execute generated command files.
- [ ] Connect to any database.
- [ ] Execute row-copy.
- [ ] Authorize production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
