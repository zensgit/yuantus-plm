# TODO — Phase 3 Tenant Import Runbook Operator Safety Contracts

Date: 2026-05-05

## Scope

- [x] Add runbook contract for env-file static validation before source.
- [x] Add runbook contract for generated command-file validation without
  execution.
- [x] Add readiness-status contract preserving external operator evidence as
  blocked.
- [x] Align full-closeout runbook wording with source-before-precheck contract.
- [x] Add design and verification documentation.

## Still External

- [ ] Operator supplies real non-production DSNs.
- [ ] Operator runs the approved command path during the rehearsal window.
- [ ] Reviewer checks real evidence artifacts.

## Explicit Non-Goals

- [ ] Database connectivity checks.
- [ ] Row-copy execution.
- [ ] Evidence acceptance.
- [ ] Runtime tenant-mode enablement.
- [ ] Production cutover.
