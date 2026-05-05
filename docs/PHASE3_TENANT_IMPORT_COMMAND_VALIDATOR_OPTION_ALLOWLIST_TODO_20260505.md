# TODO - Phase 3 Tenant Import Command Validator Option Allowlist

Date: 2026-05-05

## Scope

- [x] Track the current generated command step while validating command files.
- [x] Restrict option lines to the command step they belong to.
- [x] Reject unknown option lines such as `--confirm-cutover`.
- [x] Reject known option lines in the wrong command block.
- [x] Reject orphan option lines outside generated command blocks.
- [x] Avoid echoing rejected option-line values.
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
