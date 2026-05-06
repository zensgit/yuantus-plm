# TODO - Phase 3 Tenant Import Shell Test Python Resolution

Date: 2026-05-06

## Scope

- [x] Add shared shell-wrapper test environment helper.
- [x] Use `sys.executable` for real Python wrapper execution in affected tests.
- [x] Preserve fake `PYTHON` overrides for guard tests that assert Python is not invoked.
- [x] Remove hard dependency on `$repo_root/.venv/bin/python`.
- [x] Remove fallback dependency on a `python` binary being available on `PATH`.
- [x] Verify affected shell-wrapper tests.
- [x] Verify the full tenant import rehearsal test family.
- [x] Add verification MD and delivery-doc index entries.

## Explicitly Still External

- [ ] Operator fills a repo-external env file with real non-production DSNs.
- [ ] Operator runs the PostgreSQL rehearsal during the approved window.
- [ ] Reviewer accepts real operator evidence.

## Explicit Non-Goals

- [ ] Change production shell wrappers.
- [ ] Connect to any database.
- [ ] Execute row-copy.
- [ ] Accept or synthesize operator evidence.
- [ ] Authorize production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
