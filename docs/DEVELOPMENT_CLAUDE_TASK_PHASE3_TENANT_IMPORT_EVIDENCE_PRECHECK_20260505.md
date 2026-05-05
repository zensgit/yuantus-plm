# Development Task — Phase 3 Tenant Import Evidence Precheck

Date: 2026-05-05

## 1. Goal

Add a DB-free shell entrypoint that validates real operator evidence before the
operator runs the evidence closeout chain.

## 2. Context

P3.4 remains externally blocked on operator-run PostgreSQL rehearsal evidence.
Once the row-copy rehearsal and operator evidence Markdown exist, the fastest
failure point should be a cheap local evidence precheck, not the later archive
or reviewer-packet stage.

## 3. Required Output

- `scripts/precheck_tenant_import_rehearsal_evidence.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py`
- `docs/PHASE3_TENANT_IMPORT_EVIDENCE_PRECHECK_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EVIDENCE_PRECHECK_20260505.md`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` update
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md` update
- `docs/DELIVERY_DOC_INDEX.md` update

## 4. Contract

The shell entrypoint must:

- require rehearsal JSON, implementation packet JSON, operator evidence MD, and
  artifact prefix;
- run the existing `tenant_import_rehearsal_evidence` validator;
- write evidence JSON/Markdown reports to default artifact-prefix paths unless
  explicit output paths are supplied;
- exit non-zero in strict mode when evidence is not accepted;
- keep `Ready for cutover: false`;
- never print database URL values.

## 5. Non-Goals

- No database connection.
- No row-copy execution.
- No operator evidence synthesis.
- No archive, redaction, intake, or reviewer-packet generation.
- No production cutover authorization.

## 6. Verification

Run:

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
