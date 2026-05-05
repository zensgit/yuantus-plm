# TODO — Phase 3 Tenant Import Command Pack Env File

Date: 2026-05-05

## Scope

- [x] Add `--env-file` to the command printer.
- [x] Print env-file template generation before row-copy commands.
- [x] Print env-file precheck before env loading.
- [x] Print safe env-file loading before row-copy.
- [x] Add `--env-file` to the command-pack wrapper.
- [x] Run env-file precheck before the operator precheck.
- [x] Preserve existing direct env-var flow.
- [x] Update tests, runbook, scripts index, and doc index.

## Still External

- [ ] Operator edits the env-file with real non-production DSNs.
- [ ] Operator runs the generated command file or full-closeout wrapper during the rehearsal window.
- [ ] Reviewer checks generated reviewer packet from real evidence.

## Explicit Non-Goals

- [ ] Database connectivity check.
- [ ] Row-copy execution during command generation.
- [ ] Secret manager integration.
- [ ] Production cutover.
