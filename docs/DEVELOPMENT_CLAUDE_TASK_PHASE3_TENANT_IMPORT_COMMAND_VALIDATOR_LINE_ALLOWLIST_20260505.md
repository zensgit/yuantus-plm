# Development Task - Phase 3 Tenant Import Command Validator Line Allowlist

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import generated command-file validator so it accepts
only the executable command lines emitted by
`scripts/print_tenant_import_rehearsal_commands.sh`.

The goal is to prevent an edited operator command file from adding extra
commands such as `rm`, `ssh`, `python -c`, `export`, or shell-control syntax
while still passing static validation.

## 2. Background

The validator already checked:

- shell syntax;
- required command steps;
- source/target URL references use quoted uppercase env vars;
- required step ordering;
- forbidden DSN, cutover, remote-control, and env-printing patterns.

It did not reject arbitrary extra executable lines that did not match a known
forbidden pattern. That left a local safety gap in the DB-free review path.

## 3. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_LINE_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_LINE_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

The validator scans every non-comment, non-blank line after `bash -n` syntax
validation.

Allowed line shapes are limited to:

- the known generated script command lines;
- `set -a` / `set +a`;
- the generated `. "<env-file>"` source line;
- generated option continuation lines beginning with `--`.

Any other executable line fails with a redacted line-number error. The error
does not echo the rejected line, so a malicious line containing a database URL
literal does not leak secret material through validator output.

## 5. Acceptance Criteria

- A generated command file still passes validation.
- Extra `rm` commands fail validation.
- Extra `python -c` commands fail validation without echoing embedded secrets.
- Extra `export PATH=...` commands fail validation.
- Shell-control lines with `;`, `&&`, `||`, pipe, command substitution, or
  backticks fail validation without echoing the line.
- The fix remains DB-free and does not execute the command file.
- P3.4 real operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No generated command execution.

## 7. Verification

Run:

```bash
bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
