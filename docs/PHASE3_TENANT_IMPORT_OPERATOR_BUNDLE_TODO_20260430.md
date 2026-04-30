# TODO — Phase 3 Tenant Import Operator Bundle

Date: 2026-04-30

## Done

- [x] Add DB-free operator bundle generator.
- [x] Consume existing operator request JSON only.
- [x] Emit JSON and Markdown reports.
- [x] Include row-copy stage environment checks.
- [x] Preserve archive-ready manual-review flow.
- [x] Keep `ready_for_cutover=false`.
- [x] Add focused unit tests.
- [x] Add runbook command section.
- [x] Add development and verification docs.
- [x] Add delivery-doc index entries.

## Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Run row-copy against an external non-production PostgreSQL target.
- [ ] Mark P3.4 rehearsal complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
