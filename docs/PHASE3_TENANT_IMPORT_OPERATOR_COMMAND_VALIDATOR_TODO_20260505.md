# TODO — Phase 3 Tenant Import Operator Command Validator

Date: 2026-05-05

## Scope

- [x] Add a DB-free operator command-file validator.
- [x] Check generated command-file shell syntax.
- [x] Check required P3.4 command steps are present.
- [x] Reject raw PostgreSQL URL literals.
- [x] Reject cutover authorization markers.
- [x] Reject remote-control command patterns.
- [x] Wire validator into command-pack generation.
- [x] Update runbook, scripts index, and doc index.

## Still External

- [ ] Operator edits the env file with real non-production DSNs.
- [ ] Operator runs the generated command file or full-closeout wrapper during the rehearsal window.
- [ ] Reviewer checks generated reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Executing generated command files.
- [ ] Database connectivity check.
- [ ] Row-copy execution.
- [ ] Production cutover.
