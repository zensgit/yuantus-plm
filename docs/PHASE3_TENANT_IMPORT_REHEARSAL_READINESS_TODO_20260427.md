# TODO — Phase 3 Tenant Import Rehearsal Readiness

Date: 2026-04-27

## Implementation

- [x] Add readiness report builder.
- [x] Add readiness CLI.
- [x] Validate intake schema version.
- [x] Validate required external inputs.
- [x] Validate non-production DSN is PostgreSQL-shaped.
- [x] Redact DSN in JSON and Markdown reports.
- [x] Validate P3.4.1 dry-run schema and readiness.
- [x] Validate pilot tenant and target schema match the dry-run report.
- [x] Support `--strict` blocker exit.

## Tests

- [x] Ready intake passes.
- [x] DSN password is redacted.
- [x] Missing owner blocks.
- [x] Unsigned classification blocks.
- [x] Non-PostgreSQL DSN blocks.
- [x] Dry-run not-ready blocks.
- [x] Tenant/schema mismatch blocks.
- [x] CLI writes JSON and Markdown.
- [x] `--strict` exits 1 when blocked.
- [x] Invalid JSON exits 2.
- [x] Source does not connect or mutate databases.

## Documentation

- [x] Add Claude task MD.
- [x] Add DEV/verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Still Blocked

- [ ] Actual import rehearsal implementation.
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.

## Verification

- [x] Focused pytest suite.
- [x] Doc/runbook index suite.
- [x] `py_compile`.
- [x] `git diff --check`.
