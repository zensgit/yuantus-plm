# Odoo18 PLM Stack Pytest Interpreter Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` compiles files with `PY_BIN` and should run
pytest with the same interpreter by default. That prevents a common local/CI
drift class where `python` comes from one environment while a bare `pytest`
binary comes from another.

This change adds a contract for that behavior.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or smoke membership was changed.

## 3. Design

The verifier already builds pytest execution through an array:

```bash
PYTEST_CMD=()
if [[ -n "${PYTEST_BIN:-}" ]]; then
  PYTEST_CMD=("${PYTEST_BIN}")
else
  PYTEST_CMD=("${PY_BIN}" -m pytest)
fi
```

The default path must stay `("${PY_BIN}" -m pytest)`, while `PYTEST_BIN` remains
an explicit override for unusual runner setups.

The script must invoke pytest through:

```bash
"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"
```

This keeps the command array safe and avoids falling back to a hard-coded
`"$PYTEST_BIN" -q ...` call.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_uses_py_bin_module_pytest_by_default
```

The test verifies:

- `PYTEST_CMD` is initialized as an array.
- `PYTEST_BIN` remains the explicit override branch.
- the default branch is `PYTEST_CMD=("${PY_BIN}" -m pytest)`.
- final invocation uses `"${PYTEST_CMD[@]}"`.
- legacy direct `"$PYTEST_BIN" -q ...` invocation is absent.

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No change to `PYTEST_BIN` override semantics.
- No new CLI flags.
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

- verifier contract: 7 passed
- CI wiring/order + verifier contract: 9 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a reproducibility guard. If the default pytest invocation changes, the
review must explain why the new path still uses the same Python environment as
the compile phase or why the explicit override path is sufficient.
