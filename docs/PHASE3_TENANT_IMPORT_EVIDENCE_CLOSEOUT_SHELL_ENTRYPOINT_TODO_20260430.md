# TODO — Phase 3 Tenant Import Evidence Closeout Shell Entrypoint

Date: 2026-04-30

## Done

- [x] Add `scripts/run_tenant_import_evidence_closeout.sh`.
- [x] Chain archive, redaction, handoff, intake, and reviewer-packet modules.
- [x] Derive redaction scan inputs from archive artifacts.
- [x] Default derived output paths from `--artifact-prefix`.
- [x] Keep strict mode enabled by default.
- [x] Preserve DB-free closeout-only scope.
- [x] Add focused shell-entrypoint tests.
- [x] Add shell syntax/index contract coverage.
- [x] Add runbook shortcut.
- [x] Add development and verification docs.
- [x] Add delivery-doc index entries.

## Not Done

- [ ] Run operator PostgreSQL row-copy rehearsal.
- [ ] Create or sign operator evidence.
- [ ] Mark P3.4 stop gate complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
