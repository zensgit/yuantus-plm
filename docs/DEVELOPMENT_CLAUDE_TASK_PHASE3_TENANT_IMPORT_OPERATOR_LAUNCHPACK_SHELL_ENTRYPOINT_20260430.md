# Development Task — Phase 3 Tenant Import Operator Launchpack Shell Entrypoint

Date: 2026-04-30

## 1. Goal

Add a repo-local shell entrypoint for the DB-free tenant import operator
launchpack so an operator can run one stable `scripts/` command instead of
remembering the Python module invocation and output-path convention.

## 2. Scope

Implement:

- `scripts/run_tenant_import_operator_launchpack.sh`;
- focused shell-entrypoint tests;
- shell syntax/index contract wiring;
- runbook §17.4 shell example;
- TODO and verification docs;
- delivery-doc and delivery-scripts index entries.

## 3. Non-Goals

Do not:

- change `tenant_import_rehearsal_operator_launchpack.py`;
- run row-copy rehearsal;
- open database connections;
- read source or target database URL values;
- accept operator evidence;
- build evidence archives;
- mark P3.4 complete;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Design

The wrapper is intentionally thin:

```text
scripts/run_tenant_import_operator_launchpack.sh
  -> python -m yuantus.scripts.tenant_import_rehearsal_operator_launchpack
```

It only:

- validates required flags;
- derives default output paths from `--artifact-prefix`;
- sets `PYTHONPATH=src`;
- selects `PYTHON`, `.venv/bin/python`, then `python`;
- passes through source/target environment variable names;
- enables `--strict` by default.

## 5. Output Defaults

Given:

```text
--artifact-prefix output/tenant_acme
```

the wrapper defaults to:

```text
output/tenant_acme_operator_execution_packet.json
output/tenant_acme_operator_execution_packet.md
output/tenant_acme_operator_flow*
output/tenant_acme_operator_launchpack.json
output/tenant_acme_operator_launchpack.md
```

## 6. Safety Contract

The wrapper must remain DB-free and launchpack-only.

It may mention source/target URL environment variable names because the
underlying operator packet emits command templates, but it must not read or
expand the secret values.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py

git diff --check
```
