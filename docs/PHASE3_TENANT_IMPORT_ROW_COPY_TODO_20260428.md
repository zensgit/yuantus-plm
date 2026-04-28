# TODO - Phase 3 Tenant Import Row Copy

Date: 2026-04-28

## Implementation

- [x] Keep implementation packet and fresh artifact guards.
- [x] Require `--confirm-rehearsal`.
- [x] Require runtime source and target URLs.
- [x] Require target URL to be PostgreSQL.
- [x] Require redacted runtime URLs to match plan/packet artifacts.
- [x] Require managed target schema pattern.
- [x] Import only `tenant_tables_in_import_order`.
- [x] Block global/control-plane tables in the plan.
- [x] Block missing `source_row_counts`.
- [x] Copy rows in batches.
- [x] Emit table-level row count results.
- [x] Emit `ready_for_rehearsal_import`.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Guarded happy path executes row-copy hook.
- [x] Missing confirmation blocks before DB work.
- [x] Missing runtime URLs block before DB work.
- [x] Non-PostgreSQL target URL blocks.
- [x] Unmanaged target schema blocks.
- [x] Global table in plan blocks.
- [x] Missing row count blocks.
- [x] Blocked packet and stale artifacts block.
- [x] Row count mismatch blocks after attempted copy.
- [x] `_copy_table` moves rows between SQLAlchemy connections.
- [x] CLI writes JSON and Markdown reports.

## Documentation

- [x] Add row-copy taskbook.
- [x] Add development and verification MD.
- [x] Update tenant migration runbook.
- [x] Update delivery doc index.

## Explicitly Not Started

- [ ] Production cutover.
- [ ] Runtime `TENANCY_MODE=schema-per-tenant` enablement.
- [ ] Automatic rollback or destructive cleanup.
- [ ] Operator-run non-production rehearsal evidence capture.
