# TODO — Phase 3 Tenant Import URL Env Name Allowlist

Date: 2026-05-05

## Implementation

- [x] Add uppercase env-var name validation to env-file precheck.
- [x] Add uppercase env-var name validation to operator precheck.
- [x] Add uppercase env-var name validation to command printer.
- [x] Add uppercase env-var name validation to command-pack wrapper.
- [x] Add uppercase env-var name validation to operator launchpack shell wrapper.
- [x] Add uppercase env-var name validation to operator sequence wrapper.
- [x] Add uppercase env-var name validation to full-closeout wrapper.
- [x] Add uppercase env-var reference validation to generated command-file validator.

## Tests

- [x] Reject invalid env names before env-file source.
- [x] Reject invalid env names before indirect shell expansion.
- [x] Reject invalid env names before Python launchpack invocation.
- [x] Reject invalid env names before writing generated command files.
- [x] Reject invalid env names in externally supplied generated command files.
- [x] Preserve supported custom uppercase env names.
- [x] Preserve DB-free and cutover-blocked boundaries.

## Documentation

- [x] Update runbook operator command-pack guidance.
- [x] Update parent rehearsal TODO.
- [x] Update readiness status.
- [x] Add development task MD.
- [x] Add verification MD.
- [x] Update delivery doc index.

## Explicitly Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Run row-copy against a real PostgreSQL database.
- [ ] Mark P3.4 rehearsal complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
