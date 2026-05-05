# TODO — Phase 3 Tenant Import Operator Safety Hardening

Date: 2026-05-05

## Scope

- [x] Enforce ordered generated operator command steps.
- [x] Require row-copy command URL inputs to use environment-variable
  references.
- [x] Reject generated command files that print DSN environment variables.
- [x] Validate env files statically before sourcing them.
- [x] Reject command substitution and non-assignment env-file lines without
  executing them.
- [x] Update runbook wording for the stricter safety gates.
- [x] Add focused regression tests.

## Still External

- [ ] Operator supplies real non-production DSNs in a repo-external env file.
- [ ] Operator runs the command pack or full-closeout wrapper during an approved
  rehearsal window.
- [ ] Reviewer checks real evidence artifacts.

## Explicit Non-Goals

- [ ] Database connectivity checks.
- [ ] Row-copy execution.
- [ ] Evidence acceptance.
- [ ] Runtime tenant-mode enablement.
- [ ] Production cutover.
