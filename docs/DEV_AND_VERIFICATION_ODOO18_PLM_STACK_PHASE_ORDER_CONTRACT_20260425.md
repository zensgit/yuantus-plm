# Odoo18 PLM Stack Phase Order Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` is expected to run the Odoo18 verification
pipeline in a fixed order:

1. report selected mode
2. run `py_compile`
3. run pytest
4. print `PASS`

This change adds a contract for that order so a future edit cannot accidentally
run pytest before compile coverage or print a success marker before all work is
complete.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or test membership was changed.

## 3. Design

The script currently ends with:

```bash
echo "[verify_odoo18_plm_stack] mode=${MODE}"
echo "[verify_odoo18_plm_stack] py_compile"
"$PY_BIN" -m py_compile "${compile_files[@]}"

echo "[verify_odoo18_plm_stack] pytest"
"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"

echo "[verify_odoo18_plm_stack] PASS"
```

The new contract pins this ordering using static positions in the script.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_runs_compile_before_pytest_and_pass_marker_last
```

The test verifies:

- mode marker appears before the compile phase marker
- compile marker appears before the `py_compile` command
- `py_compile` runs before the pytest marker
- pytest command runs before the final `PASS` marker

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No change to logging format.
- No new timing or duration metrics.
- No execution of the full suite in this contract.
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

- verifier contract: 12 passed
- CI wiring/order + verifier contract: 14 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is an execution-order guard. If the verifier pipeline changes order, the
review should explicitly justify why compile coverage no longer needs to run
before pytest or why the success marker remains trustworthy.
