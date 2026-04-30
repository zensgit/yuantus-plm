# Development Task — Phase 3 Tenant Import Operator Flow

Date: 2026-04-30

## 1. Goal

Collapse the DB-free operator handoff chain into one command.

Before this task, the operator-facing handoff required three local commands:

```text
external status -> operator request -> operator bundle
```

This task adds one DB-free flow command that runs those three report builders in
sequence, writes all six downstream artifacts, and emits a summary JSON/Markdown
report.

## 2. Scope

Implement:

- `src/yuantus/scripts/tenant_import_rehearsal_operator_flow.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_flow.py`
- runbook §17.3;
- TODO and verification docs;
- delivery-doc index entries.

## 3. Non-Goals

Do not:

- run row-copy;
- open database connections;
- import the row-copy script;
- accept operator evidence;
- build evidence archive or handoff artifacts;
- mark P3.4 complete;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Input Contract

Input is the operator execution packet JSON.

The flow calls the existing builders:

- `tenant_import_rehearsal_external_status.build_external_status_report`
- `tenant_import_rehearsal_operator_request.build_operator_request_report`
- `tenant_import_rehearsal_operator_bundle.build_operator_bundle_report`

The flow should not duplicate their validation logic.

## 5. Output Contract

The summary report uses schema version:

```text
p3.4.2-tenant-import-rehearsal-operator-flow-v1
```

It writes:

- external status JSON/Markdown;
- operator request JSON/Markdown;
- operator bundle JSON/Markdown;
- flow summary JSON/Markdown.

It must keep `ready_for_cutover=false`.

## 6. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_flow.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_bundle.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_operator_flow.py

git diff --check
```
