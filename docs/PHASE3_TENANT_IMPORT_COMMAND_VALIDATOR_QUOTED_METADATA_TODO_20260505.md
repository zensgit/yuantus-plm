# TODO - Phase 3 Tenant Import Command Validator Quoted Metadata

Date: 2026-05-05

## Scope

- [x] Add shared quoted metadata validation for generated evidence-template fields.
- [x] Reject shell variable expansion in quoted metadata values.
- [x] Reject backslash escape syntax in quoted metadata values.
- [x] Avoid echoing rejected metadata values.
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
