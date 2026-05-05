# Dev & Verification — Phase 3 Tenant Import Command Pack Env File

Date: 2026-05-05

## 1. Summary

Updated the P3.4 operator command printer and command-pack wrapper to use the
repo-external env-file flow.

The generated command file now includes template generation, env-file precheck,
and safe env-file loading before the existing row-copy command sequence.

## 2. Files Changed

- `scripts/print_tenant_import_rehearsal_commands.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_PACK_ENV_FILE_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_PACK_ENV_FILE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_PACK_ENV_FILE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The command printer accepts `--env-file PATH`. It emits commands to:

- generate the repo-external env-file template;
- ask the operator to edit placeholders;
- run the DB-free env-file precheck;
- load the env file without printing values;
- run the existing P3.4 operator sequence.

The command-pack wrapper accepts the same `--env-file` option. When present, it
prechecks and loads the file before running the existing operator precheck.

## 4. Safety Boundaries

The change:

- does not print database URL values;
- does not connect to databases;
- does not run row-copy during command generation;
- preserves `Ready for cutover: false`;
- preserves the existing direct env-var path.

## 5. Verification Commands

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

## 6. Verification Results

- Focused command-printer and command-pack shell suites: 11 passed in 0.25s.
- Command-pack/env-file + script/doc index contracts: 48 passed in 0.98s.
- `bash -n scripts/print_tenant_import_rehearsal_commands.sh`: passed.
- `bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution is still required:

- fill the repo-external env file with real non-production DSNs;
- run the generated command file or full-closeout wrapper during the rehearsal window;
- review the generated reviewer packet.
