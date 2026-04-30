# TODO — Phase 3 Tenant Import Stop-Gate Contracts

Date: 2026-04-30

## Contracts

- [x] Assert parent P3.4 TODO keeps real operator evidence unchecked.
- [x] Assert runbook warns synthetic output is not operator-run evidence.
- [x] Assert synthetic drill runtime keeps evidence and cutover gates closed.
- [x] Assert synthetic drill source does not call archive or handoff gates.
- [x] Assert design and verification docs keep the external evidence gap visible.

## Verification

- [x] Run new stop-gate contracts.
- [x] Run synthetic drill focused tests.
- [x] Run full P3.4 focused suite.
- [x] Run doc-index and runbook contracts.
- [x] Run `git diff --check`.

## Explicitly Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Mark P3.4 stop gate complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
