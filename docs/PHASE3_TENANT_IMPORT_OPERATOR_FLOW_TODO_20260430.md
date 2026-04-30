# TODO — Phase 3 Tenant Import Operator Flow

Date: 2026-04-30

## Done

- [x] Add DB-free operator flow command.
- [x] Reuse existing external status, operator request, and operator bundle builders.
- [x] Emit all downstream JSON/Markdown handoff artifacts.
- [x] Emit flow summary JSON/Markdown.
- [x] Keep `ready_for_cutover=false`.
- [x] Add focused tests.
- [x] Add runbook section.
- [x] Add development and verification docs.
- [x] Add delivery-doc index entries.

## Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Run row-copy against an external non-production PostgreSQL target.
- [ ] Mark P3.4 rehearsal complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
