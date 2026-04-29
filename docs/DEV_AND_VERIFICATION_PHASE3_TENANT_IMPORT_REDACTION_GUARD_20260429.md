# Dev & Verification — Phase 3 Tenant Import Redaction Guard

Date: 2026-04-29

## 1. Summary

Added a DB-free P3.4.2 artifact redaction guard for tenant import rehearsal
handoff files.

The guard scans local JSON/Markdown artifacts for plaintext PostgreSQL
passwords and fails closed before operator evidence is shared or archived.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_redaction_guard.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REDACTION_GUARD_20260429.md`
- `docs/PHASE3_TENANT_IMPORT_REDACTION_GUARD_TODO_20260429.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_REDACTION_GUARD_20260429.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The redaction guard is a local-file scanner. It accepts repeated artifact paths
and never opens database connections.

It scans for PostgreSQL URLs and blocks if the URL contains a password that is
not an accepted redaction token.

Allowed redaction tokens include:

- `***`
- `redacted`
- `<redacted>`
- `<password>`
- `<secret>`
- `xxxxx`

## 4. Secret Handling

The guard must not echo plaintext secrets. When it finds an unsafe URL, the
blocker contains only:

- file path;
- line number;
- URL rendered with `hide_password=True`.

Focused tests assert the literal plaintext password is absent from serialized
guard output.

## 5. Safety Boundaries

This PR does not:

- open database connections;
- run row-copy;
- generate or accept real operator evidence;
- build real archive manifests;
- authorize production cutover;
- import production data;
- enable `TENANCY_MODE=schema-per-tenant`.

The source-level contract test also asserts that the new script does not import
runtime tenancy mode, SQLAlchemy engines, or sessions.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
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
  src/yuantus/scripts/tenant_import_rehearsal_redaction_guard.py

git diff --check
```

## 7. Verification Results

- Redaction guard + adjacent P3.4 evidence/status + doc-index focused suite:
  `53 passed in 0.29s`.
- Full P3.4 focused suite + doc-index trio:
  `151 passed, 1 skipped, 1 warning in 1.21s`.
- Runbook/index contracts: `5 passed in 0.03s`.
- `py_compile`: passed.
- `git diff --check`: clean.

## 8. Remaining External Work

The next real transition still requires external operator execution:

- run row-copy rehearsal against non-production PostgreSQL;
- generate real operator evidence;
- run evidence gate against real operator evidence;
- build archive manifest;
- run this redaction guard against the real artifacts;
- keep production cutover blocked until separately authorized.
