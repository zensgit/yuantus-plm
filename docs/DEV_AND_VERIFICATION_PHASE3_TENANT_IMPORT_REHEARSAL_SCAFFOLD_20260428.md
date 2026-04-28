# DEV and Verification - Phase 3 Tenant Import Rehearsal Scaffold

Date: 2026-04-28

## 1. Goal

Add a safe `tenant_import_rehearsal` entrypoint that can be handed to Claude as
the first importer-shaped code path without yet importing rows.

## 2. Implementation

Added `src/yuantus/scripts/tenant_import_rehearsal.py`.

The scaffold:

- requires an implementation packet JSON;
- requires explicit `--confirm-rehearsal`;
- validates packet schema and ready state;
- re-runs fresh packet validation from next-action;
- blocks stale upstream artifacts after packet generation;
- blocks tampered packet context;
- emits JSON and Markdown reports;
- exposes `ready_for_rehearsal_scaffold` as the primary pass/fail field;
- keeps `import_executed=false`;
- keeps `db_connection_attempted=false`;
- keeps `ready_for_cutover=false`.

## 3. Tests

Added `src/yuantus/tests/test_tenant_import_rehearsal.py`.

Coverage:

- green packet plus confirmation;
- missing confirmation;
- blocked implementation packet;
- stale artifact after packet generation;
- tampered packet context;
- CLI JSON/Markdown output;
- `--strict` blocked exit;
- artifact schema drift after packet generation;
- source-level no DB / no mutation guard.

## 4. Scope Controls

This is not the row-copy importer.

No source or target DB connection is attempted. No SQLAlchemy engine/session is
created. No row export/import, DDL, DML, rollback, cleanup, runtime cutover, or
`TENANCY_MODE=schema-per-tenant` enablement is included.

## 5. Verification

Scaffold-only:

```text
9 passed
```

Full focused suite:

```text
tenant-import-rehearsal scaffold + packet/gates/doc-index: 87 passed, 1 skipped, 1 warning
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

The next safe PR is the real row-copy implementation behind this scaffold. It
must keep all current guards and add live source/target tests behind explicit
non-production PostgreSQL configuration.
