# DEV and Verification - Phase 3 Tenant Import Rehearsal Evidence Template

Date: 2026-04-29

## 1. Summary

Added a DB-free operator evidence Markdown template generator for P3.4.2 tenant
import rehearsal evidence.

The tool reads a successful row-copy rehearsal JSON report and renders the exact
sign-off block required by the rehearsal evidence gate.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_evidence_template.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_ROW_COPY_REHEARSAL_EVIDENCE_TODO_20260428.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REHEARSAL_EVIDENCE_TEMPLATE_20260429.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_REHEARSAL_EVIDENCE_TEMPLATE_20260429.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_EVIDENCE_TEMPLATE_TODO_20260429.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Boundary

This is a formatting and guard tool only.

It does not:

- connect to a database;
- re-run the rehearsal import;
- accept evidence by itself;
- authorize cutover;
- enable schema-per-tenant runtime mode.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --backup-restore-owner "<owner>" \
  --rehearsal-window "<window>" \
  --rehearsal-executed-by "<operator>" \
  --rehearsal-result pass \
  --evidence-reviewer "<reviewer>" \
  --date "<yyyy-mm-dd>" \
  --output-json output/tenant_<tenant-id>_operator_rehearsal_evidence_template.json \
  --output-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --strict
```

## 5. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
112 passed, 1 skipped, 1 warning in 1.42s
```

Runbook/index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py
```

Result:

```text
5 passed in 0.03s
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py

git diff --check
```

Result:

```text
py_compile passed
git diff --check clean
```

## 6. Remaining Work

Operator-run non-production PostgreSQL rehearsal evidence is still external and
pending. Production cutover remains blocked.
