# Development Task — Phase 3 Tenant Import Operator Bundle

Date: 2026-04-30

## 1. Goal

Reduce the time between local P3.4 readiness and external operator execution.

Add a DB-free operator bundle generator that reads the existing operator request
artifact and emits a single JSON/Markdown bundle with:

- current stage;
- required operator inputs;
- safety reminders;
- environment checks;
- exact next command or manual review instruction;
- artifact summary;
- `ready_for_cutover=false`.

## 2. Scope

Implement:

- `src/yuantus/scripts/tenant_import_rehearsal_operator_bundle.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_bundle.py`
- runbook section for the new command;
- TODO and verification docs;
- delivery-doc index entries.

## 3. Non-Goals

Do not:

- run row-copy;
- open database connections;
- import `tenant_import_rehearsal`;
- accept operator evidence;
- build archive or handoff artifacts;
- enable production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Input Contract

The generator accepts only an operator request JSON produced by:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_request ...
```

It requires:

- `schema_version` equals `p3.4.2-tenant-import-rehearsal-operator-request-v1`;
- `ready_for_operator_request=true`;
- `ready_for_cutover=false`;
- no upstream blockers.

## 5. Output Contract

The report must use schema version:

```text
p3.4.2-tenant-import-rehearsal-operator-bundle-v1
```

It must keep:

```text
ready_for_operator_bundle=true
ready_for_cutover=false
```

For command stages, include environment checks before the next command. For
`rehearsal_archive_ready`, emit a manual-review instruction instead of inventing
a command.

## 6. Safety Contracts

The test suite must assert:

- green operator request builds a ready bundle;
- DB URL env checks are included for row-copy stage;
- archive-ready stage becomes manual review;
- blocked request blocks the bundle;
- invalid schema blocks the bundle;
- CLI writes JSON and Markdown;
- strict mode exits 1 for blocked bundle;
- source stays DB-free and execution-free.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_bundle.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_operator_bundle.py

git diff --check
```
