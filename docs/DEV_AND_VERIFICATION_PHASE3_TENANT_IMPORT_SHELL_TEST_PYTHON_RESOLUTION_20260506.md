# Dev & Verification - Phase 3 Tenant Import Shell Test Python Resolution

Date: 2026-05-06

## 1. Summary

Removed clean-worktree Python interpreter assumptions from the P3.4 tenant
import shell-wrapper tests.

The affected tests now use a shared helper that sets `PYTHON` to
`sys.executable` and `PYTHONPATH` to the repository `src` directory. This keeps
the tests portable across local checkouts, temporary worktrees, and CI runners
without requiring a repository-local `.venv`.

## 2. Files Changed

- `src/yuantus/tests/tenant_import_shell_test_env.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_SHELL_TEST_PYTHON_RESOLUTION_20260506.md`
- `docs/PHASE3_TENANT_IMPORT_SHELL_TEST_PYTHON_RESOLUTION_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SHELL_TEST_PYTHON_RESOLUTION_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The new helper centralizes shell-wrapper test environment construction:

```python
env["PYTHONPATH"] = str(repo_root / "src")
env["PYTHON"] = sys.executable
```

Only tests changed. Production scripts keep their existing interpreter
resolution logic. Tests that deliberately use fake Python binaries still set
`env["PYTHON"]` inside the test body.

## 4. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  src/yuantus/tests/tenant_import_shell_test_env.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal*.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal*.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 5. Verification Results

- `py_compile`: passed.
- Affected shell-wrapper tests: 29 passed.
- Full tenant import rehearsal test family: 325 passed, 1 skipped, 1 warning.
- Focused tenant import plus doc-index regression: 329 passed, 1 skipped, 1 warning.
- `git diff --check`: clean.

## 6. Remaining Work

The P3.4 product stop gate remains external operator evidence:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
