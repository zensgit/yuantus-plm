# TODO — Phase 3 Tenant Import Env File Precheck

Date: 2026-05-05

## Scope

- [x] Add a DB-free env-file precheck.
- [x] Validate source and target database URL variable presence.
- [x] Fail on placeholder values.
- [x] Fail on non-PostgreSQL URL shapes.
- [x] Avoid printing database URL values.
- [x] Support custom source/target variable names.
- [x] Wire the precheck into the full-closeout wrapper before row-copy.
- [x] Update runbook, script index, and doc index.

## Still External

- [ ] Operator fills the repo-external env file with real non-production DSNs.
- [ ] Operator runs the full-closeout wrapper during the rehearsal window.
- [ ] Reviewer checks generated reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Database connectivity check.
- [ ] Row-copy rehearsal execution.
- [ ] Secret manager integration.
- [ ] Production cutover.
