# Development Task — Phase 3 Tenant Import Operator Precheck

Date: 2026-04-30

## 1. Goal

Add a DB-free operator precheck before the P3.4 tenant import rehearsal command
sequence is executed.

The precheck should catch missing local files, non-green implementation packets,
missing DSN environment variables, and missing helper scripts before the
operator starts the real row-copy rehearsal.

## 2. Scope

Implement:

- `scripts/precheck_tenant_import_rehearsal_operator.sh`;
- focused precheck tests;
- shell syntax/index contract wiring;
- runbook §17.4 pointer;
- TODO and verification docs;
- delivery-doc and delivery-scripts index entries.

## 3. Non-Goals

Do not:

- print DSN values;
- open database connections;
- run row-copy rehearsal;
- create or accept operator evidence;
- build archive or reviewer artifacts;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Design

The shell precheck validates:

```text
implementation packet exists
implementation packet schema is expected
ready_for_claude_importer=true
ready_for_cutover=false
blockers=[]
SOURCE_DATABASE_URL / TARGET_DATABASE_URL are set
required helper scripts are executable
```

It reports environment variable names only. It never prints secret values.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py

git diff --check
```
