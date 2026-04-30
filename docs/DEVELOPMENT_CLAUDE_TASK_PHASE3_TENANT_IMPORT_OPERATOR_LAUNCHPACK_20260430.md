# Development Task — Phase 3 Tenant Import Operator Launchpack

Date: 2026-04-30

## 1. Goal

Reduce the operator preparation path to one DB-free command.

The launchpack starts from a green implementation packet and generates:

- operator execution packet JSON/Markdown;
- external status JSON/Markdown;
- operator request JSON/Markdown;
- operator bundle JSON/Markdown;
- launchpack summary JSON/Markdown.

## 2. Scope

Implement:

- `src/yuantus/scripts/tenant_import_rehearsal_operator_launchpack.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py`
- runbook §17.4;
- TODO and verification docs;
- delivery-doc index entries.

## 3. Non-Goals

Do not:

- run row-copy;
- open database connections;
- accept operator evidence;
- build evidence archive or handoff artifacts;
- mark P3.4 complete;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Design

The launchpack composes existing builders:

```text
implementation packet
  -> operator packet
  -> external status
  -> operator request
  -> operator bundle
```

It should not duplicate lower-level validation rules.

## 5. Output Contract

The summary report uses schema version:

```text
p3.4.2-tenant-import-rehearsal-operator-launchpack-v1
```

It must keep:

```text
ready_for_operator_launchpack=true
ready_for_cutover=false
```

## 6. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_flow.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_bundle.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_operator_launchpack.py

git diff --check
```
