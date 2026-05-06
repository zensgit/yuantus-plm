# TODO - Phase 3 Tenant Import Shell Wrapper CLI Error Redaction

Date: 2026-05-05

## Scope

- [x] Stop echoing unknown CLI argument values from env-template generation.
- [x] Stop echoing unknown CLI argument values from operator precheck.
- [x] Stop echoing unknown CLI argument values from command-pack preparation.
- [x] Stop echoing unknown CLI argument values from command printing.
- [x] Stop echoing unknown CLI argument values from operator launchpack wrapper.
- [x] Stop echoing unknown CLI argument values from operator sequence wrapper.
- [x] Stop echoing unknown CLI argument values from full-closeout wrapper.
- [x] Stop echoing unknown CLI argument values from evidence precheck.
- [x] Stop echoing unknown CLI argument values from evidence closeout.
- [x] Add one parameterized regression covering all affected shell wrappers.
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
- [ ] Accept or synthesize operator evidence.
- [ ] Authorize production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
