# TODO - Phase 3 Tenant Import Command Validator Syntax Redaction

Date: 2026-05-05

## Scope

- [x] Keep `bash -n` as the generated command-file syntax gate.
- [x] Stop echoing raw `bash -n` diagnostics in validator output.
- [x] Add a redacted syntax-failure marker.
- [x] Cover syntax errors containing DSN-like text.
- [x] Avoid echoing rejected syntax-error command lines.
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
