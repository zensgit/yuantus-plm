# Dev & Verification — Phase 3 Tenant Import Evidence Precheck

Date: 2026-05-05

## 1. Summary

Added a DB-free evidence precheck wrapper for the P3.4 tenant import rehearsal
operator path.

The wrapper validates the row-copy rehearsal report, implementation packet, and
operator evidence Markdown before evidence closeout.

## 2. Files Changed

- `scripts/precheck_tenant_import_rehearsal_evidence.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_EVIDENCE_PRECHECK_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_EVIDENCE_PRECHECK_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EVIDENCE_PRECHECK_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The wrapper delegates to:

- `python -m yuantus.scripts.tenant_import_rehearsal_evidence`

It derives default output paths from `--artifact-prefix`, keeps strict mode on
by default, and exits non-zero when evidence is not accepted.

## 4. Safety Boundaries

The wrapper:

- reads local JSON/Markdown artifacts only;
- does not print DSN values;
- does not open database connections;
- does not run row-copy rehearsal;
- does not synthesize operator evidence;
- does not build archives or reviewer packets;
- keeps cutover authorization out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/precheck_tenant_import_rehearsal_evidence.sh
git diff --check
```

## 6. Verification Results

- Focused evidence-precheck shell suite: 5 passed in 0.55s.
- Evidence precheck + evidence validator + evidence closeout shell + script/doc
  index contracts: 44 passed in 2.11s.
- `bash -n scripts/precheck_tenant_import_rehearsal_evidence.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- this wrapper only validates evidence artifacts after a real row-copy run;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
