# Odoo18 PLM Stack PY_BIN Default Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` should use the repository virtual
environment when it is present, while still remaining runnable in CI where no
`.venv` exists.

The existing behavior is:

```bash
PY_BIN="${PY_BIN:-}"
if [[ -z "$PY_BIN" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PY_BIN="${REPO_ROOT}/.venv/bin/python"
  else
    PY_BIN="python3"
  fi
fi
```

This change adds a contract so that fallback order cannot drift silently.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or smoke membership was changed.

## 3. Design

The contract asserts:

- `SCRIPT_DIR` is computed from `BASH_SOURCE[0]`
- `REPO_ROOT` is computed from `SCRIPT_DIR`
- `PY_BIN` honors an explicit environment override first
- empty `PY_BIN` falls back to `${REPO_ROOT}/.venv/bin/python` when executable
- otherwise it falls back to `python3`
- this resolution happens before `PYTEST_CMD` is built
- help text documents the `.venv/bin/python` default

This keeps local runs and CI runs aligned with the intended interpreter
resolution policy.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_defaults_py_bin_to_repo_venv_then_python3
```

The test is static because it guards script structure and documented fallback
order. It does not create or remove `.venv`.

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No change to `PY_BIN` override semantics.
- No dependency installation changes.
- No change to `smoke` or `full` test lists.
- No production/shared-dev execution.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
git diff --check
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Results:

- verifier contract: 10 passed
- CI wiring/order + verifier contract: 12 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a reproducibility guard. If the interpreter fallback order changes,
reviewers should confirm both local `.venv` execution and CI `python3`
execution remain intentional.
