# Development Task — Phase 3 Tenant Import Operator Command Validator

Date: 2026-05-05

## 1. Goal

Add a DB-free validator for generated P3.4 tenant import operator command
files.

## 2. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_VALIDATOR_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_VALIDATOR_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The validator accepts a generated command file and checks:

- shell syntax with `bash -n`;
- required P3.4 command steps are present;
- raw PostgreSQL URL literals are absent;
- cutover authorization markers are absent;
- remote-control commands such as `gh pr` and `curl` are absent.

The command-pack wrapper runs this validator after writing the command file and
before returning success.

## 4. Safety Contract

The validator must:

- not execute the generated command file;
- not connect to databases;
- not run row-copy;
- not print database URL values;
- preserve `Ready for cutover: false`;
- fail closed on missing required steps or forbidden patterns.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh
bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh
git diff --check
```
