# Development Task — Phase 3 Tenant Import Operator Command Printer

Date: 2026-04-30

## 1. Goal

Add a print-only command helper for P3.4 tenant import rehearsal operators.

The helper should produce a safe, copyable command sequence from implementation
packet through evidence closeout without reading database secrets or executing
any rehearsal step.

## 2. Scope

Implement:

- `scripts/print_tenant_import_rehearsal_commands.sh`;
- focused command-printer tests;
- shell syntax/index contract wiring;
- runbook §17.4 pointer;
- TODO and verification docs;
- delivery-doc and delivery-scripts index entries.

## 3. Non-Goals

Do not:

- execute the printed commands;
- read or print database URL values;
- open database connections;
- run row-copy rehearsal;
- create or accept operator evidence;
- build archive or reviewer artifacts;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Design

The helper takes an `--artifact-prefix` and prints commands for:

```text
operator launchpack
row-copy rehearsal
operator evidence template
evidence gate
evidence closeout
```

The printed commands use shell variable placeholders for source and target DSNs.

## 5. Safety Contract

The helper is print-only. It must not execute command substitutions, call
database clients, or embed plaintext database URL values.

## 6. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py

git diff --check
```
