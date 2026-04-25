# Odoo18 PLM Stack Shell Syntax Contract

Date: 2026-04-24

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` is now part of the router decomposition
closeout workflow. It runs py_compile coverage and the Odoo18 PLM smoke suite.
Because this script is used as a local and CI-facing verification entrypoint, it
must be included in the shared shell syntax contract.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_SHELL_SYNTAX_CONTRACT_20260424.md`

## 3. Design

The existing `test_ci_and_ops_shell_scripts_are_syntax_valid` contract already
enumerates CI and ops shell scripts that must pass `bash -n`. This change adds
`scripts/verify_odoo18_plm_stack.sh` to that list.

This is intentionally a syntax-only guard. Runtime behavior remains covered by
the explicit smoke invocation.

## 4. Non-Goals

- No behavior change in `verify_odoo18_plm_stack.sh`.
- No CI workflow restructuring.
- No smoke test expansion.

## 5. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Results:

- Shell syntax contracts: `18 passed in 0.48s`
- CI wiring + CI ordering + shell syntax contracts: `20 passed in 0.48s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.77s`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- `git diff --check`: passed

## 6. Review Notes

Review should confirm that this remains a syntax contract only. It should not
replace the runtime smoke run.
