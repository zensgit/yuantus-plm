# TODO - Phase 3 Tenant Import Command Validator Safe Path Options

Date: 2026-05-05

## Scope

- [x] Add shared safe artifact path token validation for generated path options.
- [x] Reject output redirection in path-valued options.
- [x] Reject input redirection in path-valued options.
- [x] Reject shell variable expansion in path-valued options.
- [x] Reject quoted path rewrites in path-valued options.
- [x] Avoid echoing rejected path values.
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
