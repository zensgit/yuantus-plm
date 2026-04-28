# DEV & Verification — Phase 3 Tenant Import Sign-Off Guard

Date: 2026-04-28

## 1. Goal

Harden the P3.4.2 import rehearsal readiness gate so a caller cannot pass
`--classification-signed-off` while the tracked table-classification Sign-Off
block is still blank or inconsistent with the operator inputs.

This is still pre-import guard work. It does not implement the tenant importer
and does not open database connections.

## 2. Delivered

- `src/yuantus/scripts/tenant_import_rehearsal_readiness.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_readiness.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REHEARSAL_READINESS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_READINESS_TODO_20260427.md`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The readiness validator now parses
`docs/TENANT_TABLE_CLASSIFICATION_20260427.md` §6 (`## 6. Sign-Off`) and
extracts the fenced text block fields:

- `Pilot tenant`
- `PostgreSQL rehearsal DSN`
- `Backup/restore owner`
- `Rehearsal window`
- `Reviewer`
- `Decision`
- `Date`

Readiness remains false unless every field is non-empty and non-placeholder.
The `Decision` value must be an approved value. Pilot tenant,
backup/restore owner, and rehearsal window must match the CLI inputs.

For the rehearsal DSN, the tracked document must contain a redacted PostgreSQL
URL such as `postgresql://user:***@host/db`. The validator compares the parsed
driver, host, port, and database against the CLI `--target-url` without ever
persisting the plaintext password.

## 4. Scope Controls

- No `create_engine`.
- No source DB connection.
- No target DB connection.
- No schema create/drop/migration.
- No import/replay implementation.
- No production cutover or `TENANCY_MODE=schema-per-tenant` enablement.

## 5. Tests Added

- blank Sign-Off fields block readiness;
- Sign-Off pilot tenant / DSN / owner / window mismatches block readiness;
- non-URL Sign-Off DSN blocks readiness;
- PostgreSQL driver variants such as `postgresql+psycopg` do not create false
  DSN mismatch blockers;
- Markdown readiness output includes the Sign-Off summary;
- plaintext target password is absent from JSON and Markdown reports.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py

git diff --check
```

## 7. Results

```text
focused readiness/dry-run/doc-index: 23 passed, 1 warning in 0.77s
runbook/index contracts: 5 passed in 0.03s
py_compile: passed
git diff --check: clean
```

## 8. Next Step

The real P3.4.2 importer remains blocked until a readiness report has
`ready_for_rehearsal=true`. That requires the external stop-gate inputs and a
signed table-classification artifact.
