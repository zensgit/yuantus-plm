# TODO - Phase 3 Tenant Import Env File Key Allowlist

Date: 2026-05-05

## Scope

- [x] Restrict env-file assignment keys to the selected source/target URL
  variables.
- [x] Preserve custom `--source-url-env` and `--target-url-env` names.
- [x] Reject default source/target variable names when custom names are
  selected.
- [x] Reject static environment pollution keys before shell source.
- [x] Add direct precheck tests.
- [x] Add command-pack wrapper regression coverage.
- [x] Add full-closeout wrapper regression coverage.
- [x] Update runbook and readiness tracking.
- [x] Keep parent P3.4 operator-run evidence item unchecked.
- [x] Add verification MD and delivery-doc index entries.

## Explicitly Still External

- [ ] Operator fills a repo-external env file with real non-production DSNs.
- [ ] Operator runs the PostgreSQL rehearsal during the approved window.
- [ ] Reviewer accepts real operator evidence.

## Explicit Non-Goals

- [ ] Connect to any database.
- [ ] Execute row-copy.
- [ ] Authorize production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
- [ ] Print DSN values in stdout, stderr, docs, or generated command files.
