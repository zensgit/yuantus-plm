# TODO — Phase 3 Tenant Import Operator Launchpack Shell Entrypoint

Date: 2026-04-30

## Done

- [x] Add `scripts/run_tenant_import_operator_launchpack.sh`.
- [x] Default derived output paths from `--artifact-prefix`.
- [x] Keep strict mode enabled by default.
- [x] Preserve DB-free launchpack-only scope.
- [x] Add focused shell-entrypoint tests.
- [x] Add shell syntax/index contract coverage.
- [x] Add runbook example.
- [x] Add delivery-scripts index entry.
- [x] Add development and verification docs.
- [x] Add delivery-doc index entries.

## Not Done

- [ ] Run operator PostgreSQL row-copy rehearsal.
- [ ] Accept operator evidence.
- [ ] Build evidence archive.
- [ ] Sign off P3.4 stop gate.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
