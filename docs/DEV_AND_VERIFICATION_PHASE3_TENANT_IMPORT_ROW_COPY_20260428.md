# DEV and Verification - Phase 3 Tenant Import Row Copy

Date: 2026-04-28

## 1. Goal

Move `tenant_import_rehearsal` from a fail-closed scaffold to the first guarded
row-copy rehearsal path.

## 2. Implementation

Updated `src/yuantus/scripts/tenant_import_rehearsal.py`.

The command now:

- keeps all implementation packet and fresh artifact validation gates;
- requires runtime `--source-url` and `--target-url`;
- validates target URL is PostgreSQL;
- validates redacted runtime URLs match the plan/packet artifacts;
- validates target schema is managed;
- validates the plan allowlist contains no global/control-plane table;
- validates every planned table has `source_row_counts`;
- uses stripped tenant import metadata aligned with P3.4.1 dry-run;
- copies rows table-by-table in plan order;
- reports table-level inserted row counts;
- sets `ready_for_rehearsal_import=true` only when copied row counts match;
- keeps `ready_for_cutover=false`.

## 3. Tests

Updated `src/yuantus/tests/test_tenant_import_rehearsal.py`.

Coverage includes:

- guarded happy path;
- missing confirmation;
- missing runtime URLs;
- invalid target URL;
- unmanaged target schema;
- blocked packet;
- stale artifacts;
- global table in plan;
- missing row counts;
- row count mismatch;
- `_copy_table` SQLAlchemy row movement;
- CLI JSON/Markdown output.

## 4. Scope Controls

This remains a rehearsal import, not cutover.

The implementation does not create schemas, run migrations, downgrade, drop,
truncate, auto-clean, enable runtime schema-per-tenant mode, or import any
global/control-plane table.

## 5. Verification

Row-copy test file:

```text
16 passed, 1 warning
```

Full focused suite:

```text
tenant-import row-copy + packet/gates/doc-index: 94 passed, 1 skipped, 1 warning
```

Runbook and index contracts:

```text
5 passed
```

Compile and whitespace:

```text
py_compile: passed
git diff --check: clean
```

## 6. Next Step

Run a real non-production rehearsal with operator-provided DSNs and archive the
generated JSON/Markdown evidence. Production cutover remains blocked.
