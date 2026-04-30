# TODO — Phase 3 Tenant Import Operator Command Printer

Date: 2026-04-30

## Done

- [x] Add `scripts/print_tenant_import_rehearsal_commands.sh`.
- [x] Print launchpack, row-copy, evidence-template, evidence-gate, and closeout commands.
- [x] Use DSN environment variable placeholders instead of secret values.
- [x] Preserve print-only scope.
- [x] Add focused command-printer tests.
- [x] Add shell syntax/index contract coverage.
- [x] Add runbook pointer.
- [x] Add development and verification docs.
- [x] Add delivery-doc index entries.

## Not Done

- [ ] Run operator PostgreSQL row-copy rehearsal.
- [ ] Create or sign operator evidence.
- [ ] Build real evidence closeout artifacts.
- [ ] Mark P3.4 stop gate complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
