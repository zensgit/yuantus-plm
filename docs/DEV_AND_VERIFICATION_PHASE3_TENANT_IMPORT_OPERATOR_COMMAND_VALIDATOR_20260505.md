# Dev & Verification — Phase 3 Tenant Import Operator Command Validator

Date: 2026-05-05

## 1. Summary

Added `scripts/validate_tenant_import_rehearsal_operator_commands.sh` and wired
it into the command-pack wrapper.

This adds a DB-free guard between command-file generation and operator
execution. It catches missing command steps, shell syntax errors, raw DSN
literals, and cutover authorization markers without executing the generated
file.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_VALIDATOR_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_VALIDATOR_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_VALIDATOR_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The validator runs `bash -n` on the generated command file, then scans for
required and forbidden fixed strings.

Required steps include env-file template generation, env-file precheck,
env-file loading, launchpack, row-copy, evidence template, evidence gate, and
evidence closeout.

Forbidden patterns include PostgreSQL URL literals, cutover authorization
markers, `TENANCY_MODE=`, `gh pr`, `curl`, and `psql`.

## 4. Safety Boundaries

The validator:

- does not execute the generated command file;
- does not connect to databases;
- does not run row-copy;
- does not print database URL values;
- preserves `Ready for cutover: false`.

## 5. Verification Commands

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

## 6. Verification Results

- Focused command-validator and command-pack suites: 13 passed in 0.73s.
- Command-validator/printer/pack/env-file + script/doc index contracts: 55
  passed in 1.81s.
- `bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh`:
  passed.
- `bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh`:
  passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution is still required:

- fill the repo-external env file with real non-production DSNs;
- run the generated command file or full-closeout wrapper during the rehearsal window;
- review the generated reviewer packet.
