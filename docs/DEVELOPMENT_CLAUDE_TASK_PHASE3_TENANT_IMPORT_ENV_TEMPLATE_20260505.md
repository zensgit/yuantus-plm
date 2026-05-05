# Development Task — Phase 3 Tenant Import Env Template

Date: 2026-05-05

## 1. Goal

Add a small operator helper that generates a repo-external env-file template for
P3.4 tenant import rehearsal commands.

## 2. Required Output

- `scripts/generate_tenant_import_rehearsal_env_template.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_TEMPLATE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_TEMPLATE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The helper writes an env-file template containing placeholder values for:

- `SOURCE_DATABASE_URL`
- `TARGET_DATABASE_URL`

The default output path is:

```text
$HOME/.config/yuantus/tenant-import-rehearsal.env
```

The generated file is chmodded to 0600 and intended to be filled by the
operator outside the repository before running the full-closeout wrapper with
`--env-file`.

## 4. Safety Contract

The helper must:

- generate placeholders only;
- never print database URL values;
- keep the file repo-external by default;
- refuse overwrite unless `--force` is passed;
- set output mode 0600;
- not connect to any database;
- not run rehearsal row-copy;
- not authorize cutover.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/generate_tenant_import_rehearsal_env_template.sh
git diff --check
```
