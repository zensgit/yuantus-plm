# Development Task - Phase 3 Tenant Import Env File Key Allowlist

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import rehearsal env-file precheck so an operator
env file can define only the selected source and target database URL variables.

The goal is to reject environment pollution keys such as `PATH`, `PYTHON`,
`PYTHONPATH`, and `BASH_ENV` before any wrapper sources the file.

## 2. Background

The existing precheck already rejects command substitution, shell expansion,
double quotes, non-assignment lines, missing DSNs, placeholder DSNs, and
non-PostgreSQL URL shapes.

It still accepted arbitrary static assignments. A static `PATH=...` or
`PYTHON=...` line could be loaded by the command-pack or full-closeout wrapper
after the precheck returned green. That does not expose DSN values, but it can
pollute the operator process and change command resolution before row-copy.

## 3. Required Output

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_FILE_KEY_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_FILE_KEY_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

The precheck parses each non-comment assignment before sourcing the env file.
The assignment key must match the configured `--source-url-env` or
`--target-url-env` value.

Allowed examples:

```bash
SOURCE_DATABASE_URL='postgresql://source.example/nonprod'
TARGET_DATABASE_URL='postgresql://target.example/nonprod'
```

Allowed with custom names:

```bash
TENANT_SOURCE_URL='postgresql://source.example/nonprod'
TENANT_TARGET_URL='postgresql://target.example/nonprod'
```

Rejected examples:

```bash
PATH='/tmp/blocked'
PYTHON='/tmp/blocked-python'
PYTHONPATH='/tmp/blocked-pythonpath'
BASH_ENV='/tmp/blocked-bash-env'
```

## 5. Acceptance Criteria

- The precheck rejects extra static keys before `source`.
- The precheck supports custom selected source/target URL variable names from
  the env file.
- The precheck rejects default names when custom names are selected.
- The command-pack wrapper does not write a generated command file when the
  env file contains an unsupported key.
- The full-closeout wrapper does not create reviewer artifacts when the env
  file contains an unsupported key.
- Error output includes variable names only and never prints database URLs.
- P3.4 real operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No secret manager integration.
- No change to generated tenant import commands beyond precheck gating.

## 7. Verification

Run:

```bash
bash -n \
  scripts/precheck_tenant_import_rehearsal_env_file.sh \
  scripts/prepare_tenant_import_rehearsal_operator_commands.sh \
  scripts/run_tenant_import_rehearsal_full_closeout.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
