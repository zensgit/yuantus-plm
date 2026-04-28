# DEV and Verification - Phase 3 Tenant Import Row-Copy Rehearsal Evidence

Date: 2026-04-28

## 1. Summary

Added an offline P3.4.2 rehearsal evidence gate after the row-copy importer.

The new CLI validates a real rehearsal JSON report, its implementation packet,
and an operator evidence Markdown sign-off. It does not open database
connections and cannot authorize cutover.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_evidence.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_ROW_COPY_TODO_20260428.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_ROW_COPY_REHEARSAL_EVIDENCE_20260428.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ROW_COPY_REHEARSAL_EVIDENCE_20260428.md`
- `docs/PHASE3_TENANT_IMPORT_ROW_COPY_REHEARSAL_EVIDENCE_TODO_20260428.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Runtime Boundary

The new script is intentionally DB-free.

It only reads:

- row-copy rehearsal JSON;
- implementation packet JSON;
- operator evidence Markdown.

It writes:

- evidence JSON;
- evidence Markdown.

It never imports rows, connects to a database, mutates schema, or changes
runtime tenancy mode.

## 4. Evidence Contract

The gate accepts evidence only when:

- row-copy rehearsal succeeded;
- DB connection was attempted by the row-copy tool;
- row-copy report has no blockers;
- implementation packet still matches the rehearsal context;
- implementation packet fresh-revalidates all upstream artifacts;
- table results are non-empty and row counts match;
- no global/control-plane table appears in table results;
- operator evidence sign-off is complete;
- operator tenant and rehearsal DB match the rehearsal report.

Even on success, the report keeps `ready_for_cutover=false`.

## 5. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --operator-evidence-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --output-json output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_evidence.md \
  --strict
```

## 6. Test Coverage

`test_tenant_import_rehearsal_evidence.py` covers:

- green evidence path;
- missing operator evidence;
- incomplete sign-off fields;
- mismatched tenant and rehearsal DB;
- blocked rehearsal report;
- row-count mismatch;
- global/control-plane table leakage;
- implementation packet mismatch;
- stale upstream artifact detection;
- CLI JSON/Markdown output;
- strict-mode failure;
- source guard that confirms the evidence gate remains offline.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q \
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
105 passed, 1 skipped, 1 warning in 1.08s
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
  src/yuantus/scripts/tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py

git diff --check
```

Result:

```text
py_compile passed
git diff --check clean
```

## 8. Remaining Work

Operator-run non-production PostgreSQL rehearsal evidence is still pending.

Production cutover remains blocked and is not authorized by this PR.
