# Development Task — Phase 3 Tenant Import Full Closeout Env File

Date: 2026-05-05

## 1. Goal

Reduce P3.4 operator command friction by letting the full-closeout wrapper load
source and target database URL environment variables from a repo-external env
file.

## 2. Required Output

- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_ENV_FILE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_ENV_FILE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

Add optional `--env-file PATH` to the existing full-closeout wrapper.

The wrapper sources the file with exported variables before invoking the
operator sequence wrapper. This keeps the existing child command contract
unchanged: `SOURCE_DATABASE_URL` and `TARGET_DATABASE_URL` remain the default
source and target variable names, with `--source-url-env` and `--target-url-env`
still supported for alternate names.

## 4. Safety Contract

The implementation must:

- keep `--env-file` optional;
- fail fast if the supplied env file does not exist;
- never print source or target database URL values;
- keep the env file outside repo guidance in the runbook;
- preserve both explicit confirmation gates;
- preserve `Ready for cutover: false`;
- not enable runtime schema-per-tenant mode.

## 5. Non-Goals

- No production database import.
- No production cutover authorization.
- No new secret manager integration.
- No automatic env-file generation.
- No change to the evidence closeout chain.

## 6. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh
git diff --check
```
