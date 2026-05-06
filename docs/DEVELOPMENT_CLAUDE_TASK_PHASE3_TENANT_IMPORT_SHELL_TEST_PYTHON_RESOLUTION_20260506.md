# Development Task - Phase 3 Tenant Import Shell Test Python Resolution

Date: 2026-05-06

## 1. Goal

Make the P3.4 tenant import shell-wrapper tests run in clean worktrees that do
not have a repository-local `.venv/bin/python` or a `python` executable on
`PATH`.

This is test-infrastructure hardening only. It does not change production shell
wrappers, tenant import runtime behavior, operator evidence state, or P3.4
stop-gate semantics.

## 2. Background

The P3.4 tenant import shell wrapper tests previously mixed two assumptions:

- some tests forced `PYTHON=$repo_root/.venv/bin/python`;
- some tests omitted `PYTHON`, so wrappers fell back to `python`.

Those assumptions fail in temporary or CI-like worktrees where `.venv` is not
materialized and `python3` is the only interpreter. The failure mode is
environmental and hides real regression signal:

```text
No such file or directory: .venv/bin/python
python: command not found
```

## 3. Required Output

- `src/yuantus/tests/tenant_import_shell_test_env.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py`
- `docs/PHASE3_TENANT_IMPORT_SHELL_TEST_PYTHON_RESOLUTION_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SHELL_TEST_PYTHON_RESOLUTION_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Add a small test helper:

```python
def shell_test_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["PYTHON"] = sys.executable
    return env
```

The helper keeps wrapper tests on the same interpreter running pytest. Tests
that intentionally inject fake Python executables still override `PYTHON`
locally.

## 5. Acceptance Criteria

- No affected shell-wrapper test points `PYTHON` at `$repo_root/.venv/bin/python`.
- Shell-wrapper tests that execute real Python use `sys.executable`.
- Tests that intentionally validate pre-Python guards can still override
  `PYTHON` with a fake executable.
- The full `test_tenant_import_rehearsal*.py` suite passes in the temporary
  worktree.
- No runtime scripts are changed.

## 6. Non-Goals

- No production shell wrapper change.
- No tenant import runtime change.
- No database connection or row-copy rehearsal execution.
- No operator evidence acceptance.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 7. Verification

Run:

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

git diff --check
```
