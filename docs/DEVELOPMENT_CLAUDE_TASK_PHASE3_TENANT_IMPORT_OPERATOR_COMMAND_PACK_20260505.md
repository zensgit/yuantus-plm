# Development Task — Phase 3 Tenant Import Operator Command Pack

Date: 2026-05-05

## 1. Goal

Add a DB-free operator command-pack shell entrypoint that runs the existing
P3.4 operator precheck and writes the operator command file only when the
precheck passes.

## 2. Context

P3.4 remains blocked on external operator-run PostgreSQL rehearsal evidence.
The repository already has a precheck helper and a command-printer helper, but
operators must remember to run them in the correct order.

This task reduces execution friction without weakening the stop gate.

## 3. Required Output

- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PACK_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PACK_20260505.md`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` update
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md` update
- `docs/DELIVERY_DOC_INDEX.md` update

## 4. Contract

The new shell entrypoint must:

- require `--artifact-prefix` and `--output`;
- accept the same source/target DSN environment variable names as the precheck
  and command-printer helpers;
- run `precheck_tenant_import_rehearsal_operator.sh` first;
- not write the output command file if precheck fails;
- write command-printer output to the requested path when precheck passes;
- create the output directory when needed;
- print only DSN environment variable names, never values;
- keep `Ready for cutover: false`.

## 5. Non-Goals

- No database connection.
- No row-copy execution.
- No operator evidence acceptance.
- No archive, redaction, intake, or reviewer-packet generation.
- No production cutover authorization.
- No runtime schema-per-tenant enablement.

## 6. Verification

Run:

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
