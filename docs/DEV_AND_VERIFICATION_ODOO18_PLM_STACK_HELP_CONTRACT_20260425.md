# Odoo18 PLM Stack Help Contract

Date: 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` is now the focused Odoo18 PLM verification
entrypoint used by router-decomposition closeout work. The script accepted
`smoke` and `full`, but it did not expose a zero-side-effect help mode.

This change adds `-h` / `--help` and a contract test for the help output.

## 2. Scope

Changed:

- `scripts/verify_odoo18_plm_stack.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_HELP_CONTRACT_20260425.md`

## 3. Design

The script now defines a single `usage()` helper. Both `--help` and invalid
arguments reuse that helper:

- `--help` / `-h`: print usage to stdout and exit `0`
- invalid mode: print usage to stderr and exit `2`

The help text documents:

- `smoke`
- `full`
- `PY_BIN`
- `PYTEST_BIN`
- `PYTHONPYCACHEPREFIX`

## 4. Contract

The existing Odoo18 PLM stack contract file now executes:

```bash
bash scripts/verify_odoo18_plm_stack.sh --help
```

It asserts zero exit status, empty stderr, expected usage tokens, and no
`[verify_odoo18_plm_stack]` execution log. That confirms help is a read-only
metadata path, not a smoke trigger.

## 5. Non-Goals

- No changes to `smoke` or `full` behavior.
- No changes to selected test lists.
- No router behavior changes.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Results:

- Help + dynamic compile contract: `2 passed in 0.03s`
- CI wiring + CI ordering + help/dynamic compile contract: `4 passed in 0.04s`
- Script index related contracts: `3 passed in 0.25s`
- Doc index contracts: `3 passed in 0.04s`
- Odoo18 PLM stack smoke: `265 passed in 19.83s`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- `git diff --check`: passed

## 7. Review Notes

Review should confirm help exits before py_compile and pytest execution.
