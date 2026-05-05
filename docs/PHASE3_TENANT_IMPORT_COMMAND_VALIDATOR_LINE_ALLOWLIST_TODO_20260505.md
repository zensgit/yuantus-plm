# TODO - Phase 3 Tenant Import Command Validator Line Allowlist

Date: 2026-05-05

## Scope

- [x] Add validator allowlist for generated executable command lines.
- [x] Preserve generated command-file acceptance.
- [x] Reject extra `rm` command lines.
- [x] Reject extra `python -c` command lines without echoing embedded secrets.
- [x] Reject extra `export PATH=...` command lines.
- [x] Reject shell-control syntax without echoing the rejected line.
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
