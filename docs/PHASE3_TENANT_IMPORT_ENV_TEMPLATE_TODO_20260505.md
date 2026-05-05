# TODO — Phase 3 Tenant Import Env Template

Date: 2026-05-05

## Scope

- [x] Add a repo-external env-file template generator.
- [x] Default output to `$HOME/.config/yuantus/tenant-import-rehearsal.env`.
- [x] Write placeholder source and target DSN variables.
- [x] Set generated file mode to 0600.
- [x] Refuse accidental overwrite without `--force`.
- [x] Avoid printing database URL values.
- [x] Add shell tests.
- [x] Update runbook, script index, and doc index.

## Still External

- [ ] Operator edits the generated template with real non-production DSNs.
- [ ] Operator runs the full-closeout wrapper during the rehearsal window.
- [ ] Reviewer checks generated reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Secret manager integration.
- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Database connection or row-copy execution.
