# Dev & Verification — Phase 3 Tenant Import Operator Sequence

Date: 2026-05-05

## 1. Summary

Added a single operator sequence wrapper for P3.4 tenant import rehearsal.

The wrapper chains the existing precheck, launchpack, row-copy, evidence
template, and evidence-precheck tools behind one explicit command.

## 2. Files Changed

- `scripts/run_tenant_import_rehearsal_operator_sequence.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_SEQUENCE_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_SEQUENCE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_SEQUENCE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The wrapper executes:

1. `precheck_tenant_import_rehearsal_operator.sh`
2. `run_tenant_import_operator_launchpack.sh`
3. `python -m yuantus.scripts.tenant_import_rehearsal`
4. `python -m yuantus.scripts.tenant_import_rehearsal_evidence_template`
5. `precheck_tenant_import_rehearsal_evidence.sh`

It reduces the external operator path without weakening the real rehearsal
requirement.

## 4. Safety Boundaries

The wrapper:

- requires `--confirm-rehearsal`;
- reads source/target database URLs from environment variables;
- does not print database URL values;
- does not build evidence closeout archives;
- does not produce reviewer packets;
- does not authorize production cutover;
- keeps runtime schema-per-tenant enablement out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/run_tenant_import_rehearsal_operator_sequence.sh
git diff --check
```

## 6. Verification Results

- Focused operator-sequence shell suite: 5 passed in 0.56s.
- Operator sequence + precheck + launchpack + evidence precheck + script/doc
  index contracts: 43 passed in 2.36s.
- `bash -n scripts/run_tenant_import_rehearsal_operator_sequence.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution is still required:

- real non-production PostgreSQL source/target DSNs;
- rehearsal window;
- operator-run wrapper execution;
- evidence closeout after evidence precheck is green.
