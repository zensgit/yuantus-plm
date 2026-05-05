# Development Task — Phase 3 Tenant Import Command Pack Env File

Date: 2026-05-05

## 1. Goal

Wire the P3.4 operator command printer and command-pack wrapper into the
repo-external env-file flow.

## 2. Required Output

- `scripts/print_tenant_import_rehearsal_commands.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_PACK_ENV_FILE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_PACK_ENV_FILE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The command printer now emits:

1. env-file template generation;
2. operator edit instruction;
3. env-file precheck;
4. safe env-file load;
5. existing launchpack, row-copy, evidence template, evidence gate, and closeout commands.

The command-pack wrapper accepts `--env-file`, validates it with the DB-free
env-file precheck, loads it for the existing operator precheck, and passes the
same env-file path into the generated command file.

## 4. Safety Contract

The change must:

- not print database URL values;
- not connect to either database during command generation;
- not run row-copy during command generation;
- not authorize cutover;
- preserve direct env-var operation when `--env-file` is omitted;
- fail before writing command files when env-file validation fails.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/print_tenant_import_rehearsal_commands.sh
bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh
git diff --check
```
