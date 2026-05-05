# TODO — Phase 3 Tenant Import Full Closeout Env File

Date: 2026-05-05

## Scope

- [x] Add optional `--env-file PATH`.
- [x] Source repo-external env file before the operator sequence wrapper runs.
- [x] Preserve existing direct environment variable behavior.
- [x] Preserve `--source-url-env` and `--target-url-env`.
- [x] Fail when `--env-file` points to a missing file.
- [x] Add test coverage proving DSN values are not printed.
- [x] Update runbook usage.
- [x] Update delivery script and doc index entries.

## Still External

- [ ] Operator creates the repo-external env file with real non-production DSNs.
- [ ] Operator runs the wrapper during the rehearsal window.
- [ ] Reviewer checks generated reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Secret manager integration.
- [ ] Automatic rollback or destructive cleanup.
