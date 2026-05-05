# Dev & Verification — Phase 3 Tenant Import Operator Safety Hardening

Date: 2026-05-05

## 1. Summary

Hardened the P3.4 DB-free operator safety gates.

The command-file validator now checks ordered operator steps, requires row-copy
URL arguments to come from environment variables, and rejects command files that
print environment variable values.

The env-file precheck now validates env-file syntax before sourcing. It rejects
command substitution, shell expansion syntax, double-quoted values, and
non-assignment commands before any env-file content can execute.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_SAFETY_HARDENING_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_SAFETY_HARDENING_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_SAFETY_HARDENING_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The command-file validator remains non-executing. It uses fixed-string line
ordering to ensure the generated command sequence remains:

1. env template generation
2. env-file precheck
3. env export start
4. env export end
5. operator launchpack
6. row-copy rehearsal
7. evidence template
8. evidence gate
9. evidence closeout

The env-file precheck now applies a static allowlist before source:

- comments;
- blank lines;
- static `KEY=VALUE`;
- static `export KEY=VALUE`.

Values that need quoting must be single-quoted. Double quotes and shell
expansion syntax are rejected because they can perform runtime expansion while
the file is sourced.

## 4. Security Properties

- Command substitution in env files is rejected before execution.
- Bare commands in env files are rejected before execution.
- DSN values remain absent from stdout and stderr.
- Generated command files cannot print DSN env vars through common shell
  patterns.
- All tools continue to report `Ready for cutover: false`.

## 5. Verification Commands

```bash
bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh
bash -n scripts/precheck_tenant_import_rehearsal_env_file.sh
bash -n scripts/prepare_tenant_import_rehearsal_operator_commands.sh
bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 6. Verification Results

- Script syntax: passed.
- Focused command/env-file safety tests: 21 passed in 0.82s.
- Wrapper and shell-script regression: 51 passed in 3.30s.
- Combined safety/wrapper/doc-index suite: 55 passed in 2.77s.
- `git diff --check`: clean.

## 7. Remaining Work

No local tool can complete P3.4. The remaining work is still external operator
execution:

- provide real non-production DSNs;
- run the approved command pack or full-closeout wrapper;
- generate real operator evidence;
- complete reviewer packet review.

This PR does not change the stop gate.
