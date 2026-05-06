# TODO - Phase 3 Tenant Import Python CLI Error Redaction

Date: 2026-05-06

## Scope

- [x] Add shared tenant import redacting `ArgumentParser`.
- [x] Move every `tenant_import_rehearsal*.py` CLI parser to the shared helper.
- [x] Preserve usage output and exit code `2` for parse-time failures.
- [x] Add one parameterized regression covering all affected Python module CLIs.
- [x] Update runbook and readiness tracking.
- [x] Keep parent P3.4 operator-run evidence item unchecked.
- [x] Add verification MD and delivery-doc index entries.

## Explicitly Still External

- [ ] Operator fills a repo-external env file with real non-production DSNs.
- [ ] Operator runs the PostgreSQL rehearsal during the approved window.
- [ ] Reviewer accepts real operator evidence.

## Explicit Non-Goals

- [ ] Connect to any database.
- [ ] Execute row-copy.
- [ ] Accept or synthesize operator evidence.
- [ ] Authorize production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
