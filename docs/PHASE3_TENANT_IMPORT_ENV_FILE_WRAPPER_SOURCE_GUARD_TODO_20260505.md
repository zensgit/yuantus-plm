# TODO — Phase 3 Tenant Import Env-File Wrapper Source Guard

Date: 2026-05-05

## Scope

- [x] Add command-pack wrapper regression for unsafe env-file source guard.
- [x] Add full-closeout wrapper regression for unsafe env-file source guard.
- [x] Assert command substitution is not executed.
- [x] Assert downstream artifacts are not produced after env-file rejection.
- [x] Assert DSN values remain absent from stdout/stderr.
- [x] Add design and verification documentation.

## Still External

- [ ] Operator supplies real non-production DSNs.
- [ ] Operator runs the command pack or full-closeout wrapper during an approved
  rehearsal window.
- [ ] Reviewer checks real evidence artifacts.

## Explicit Non-Goals

- [ ] Database connectivity checks.
- [ ] Row-copy execution.
- [ ] Evidence acceptance.
- [ ] Runtime tenant-mode enablement.
- [ ] Production cutover.
