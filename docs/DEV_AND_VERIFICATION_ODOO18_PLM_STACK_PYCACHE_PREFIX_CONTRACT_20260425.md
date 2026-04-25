# Odoo18 PLM Stack Pycache Prefix Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` runs both `py_compile` and pytest. Without
a stable `PYTHONPYCACHEPREFIX`, verification can leave `__pycache__` files in
the working tree or behave differently across local and CI runs.

The script already exports:

```bash
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/yuantus-pyc}"
```

This change adds a contract that pins that default and its position before any
Python work starts.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or smoke membership was changed.

## 3. Design

The contract asserts:

- the script exports `PYTHONPYCACHEPREFIX` with default `/tmp/yuantus-pyc`
- the export happens before `compile_files` setup
- the export happens before `py_compile`
- the export happens before pytest
- `PYTHONPYCACHEPREFIX` appears only in help text plus the single export

That keeps both compile and test phases under the same pycache policy.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_exports_pycache_prefix_before_python_work
```

The test is intentionally static. Its purpose is to prevent drift in the
verification script structure, not to create temporary pycache directories.

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No change to `PYTHONPYCACHEPREFIX` override semantics.
- No pycache cleanup command.
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

- verifier contract: 8 passed
- CI wiring/order + verifier contract: 10 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a reproducibility guard. If the pycache directory policy changes, the
review should explain whether the new location is still outside the repository
and why both compile and pytest phases share it.
