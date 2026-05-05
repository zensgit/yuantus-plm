# Development Task — Phase 3 Tenant Import Runbook Operator Safety Contracts

Date: 2026-05-05

## 1. Goal

Promote the P3.4 operator safety wording from documentation intent into a test
contract.

Recent DB-free hardening added:

- env-file static validation before source;
- generated command-file validation without execution;
- readiness status wording that keeps operator evidence external.

This task pins those claims so future runbook edits cannot silently weaken the
operator handoff boundary.

## 2. Scope

Modify:

- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_DOC_INDEX.md`

Add:

- this development task;
- a TODO record;
- a development and verification record.

## 3. Contract Requirements

The tests must assert:

- the runbook says env files are statically validated before loading;
- the runbook says unsafe env-file syntax is rejected before source;
- the full-closeout section places the env-file precheck before the wrapper
  command;
- the command-file validator is documented as a non-executing gate;
- the command-file validator documents step order, env-var URL references, and
  forbidden DSN/cutover/remote-control patterns;
- readiness status remains blocked on real operator-run PostgreSQL evidence.

## 4. Non-Goals

Do not:

- add a new shell script;
- change runtime wrapper behavior;
- execute row-copy;
- connect to databases;
- accept evidence;
- mark P3.4 ready for cutover.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 6. Exit Criteria

- Stop-gate contract suite passes.
- Wrapper/env-file safety regressions still pass.
- Doc-index contracts pass after new docs are indexed.
- The remaining P3.4 blocker is still external operator execution.
