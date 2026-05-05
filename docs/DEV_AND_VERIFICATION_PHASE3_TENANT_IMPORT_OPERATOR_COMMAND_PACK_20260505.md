# Dev & Verification — Phase 3 Tenant Import Operator Command Pack

Date: 2026-05-05

## 1. Summary

Added a DB-free command-pack wrapper for P3.4 tenant import rehearsal operator
execution.

The wrapper runs the existing operator precheck first and writes the operator
command file only if the precheck passes.

## 2. Files Changed

- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PACK_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PACK_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PACK_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The wrapper composes two already-tested helpers:

- `precheck_tenant_import_rehearsal_operator.sh`;
- `print_tenant_import_rehearsal_commands.sh`.

It fails closed because `set -euo pipefail` stops before the command-printer
step when precheck returns non-zero. This means no command file is written for
a missing implementation packet, missing DSN environment variables, or a
non-green implementation packet.

## 4. Safety Boundaries

The wrapper:

- reports DSN environment variable names only;
- does not print DSN values;
- does not open database connections;
- does not run row-copy rehearsal;
- does not accept operator evidence;
- does not build archives or reviewer packets;
- keeps cutover authorization out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh
git diff --check
```

## 6. Verification Results

- Focused command-pack shell suite: 5 passed in 0.19s.
- Command-pack + precheck + command-printer + script/doc index contracts: 38
  passed in 0.92s.
- `bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh`:
  passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- this wrapper only prepares commands after local precheck succeeds;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
